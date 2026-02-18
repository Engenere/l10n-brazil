# Copyright 2026 Engenere (<https://engenere.one>).
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, fields, http
from odoo.http import request


class DfeDocumentBannerController(http.Controller):
    @http.route("/l10n_br_fiscal_dfe/document_banner", auth="user", type="json")
    def document_banner(self):
        company = request.env.company
        DfeRecord = request.env["l10n_br_fiscal_dfe.dfe"]
        DfeDocument = request.env["l10n_br_fiscal_dfe.document"]

        pending_import_count = DfeRecord.search_count(
            [
                ("company_id", "=", company.id),
                ("dfe_nfe_document_type", "=", "dfe_nfe_complete"),
                ("imported_document_id", "=", False),
            ]
        )

        today = fields.Date.context_today(DfeDocument)
        today_domain = [
            ("company_id", "=", company.id),
            ("create_date", ">=", today),
        ]
        today_total = DfeDocument.search_count(today_domain)
        today_third_party = DfeDocument.search_count(
            today_domain + [("is_own_document", "=", False)]
        )
        today_own = DfeDocument.search_count(
            today_domain + [("is_own_document", "=", True)]
        )

        import pytz

        user_tz = pytz.timezone(request.env.user.tz or "UTC")

        last_query = company.dfe_last_query
        if last_query:
            last_query_str = last_query.astimezone(user_tz).strftime("%d/%m/%Y %H:%M")
        else:
            last_query_str = "-"

        next_query = company.dfe_next_query
        if next_query:
            next_query_str = next_query.astimezone(user_tz).strftime("%d/%m/%Y %H:%M")
        else:
            next_query_str = "-"

        nsu_synced = (
            company.last_nsu and company.max_nsu and company.last_nsu >= company.max_nsu
        )

        inactivity_warning = False
        inactivity_message = ""
        now = fields.Datetime.now()
        if company.dfe_last_query:
            inactivity_days = (now - company.dfe_last_query).days
            if inactivity_days > 30:
                inactivity_warning = True
                inactivity_message = _(
                    "Last DF-e query was %(days)s days ago. After 60 days of "
                    "inactivity, SEFAZ stops generating NSUs for this CNPJ "
                    "(no retroactive recovery).",
                    days=inactivity_days,
                )
        else:
            inactivity_warning = True
            inactivity_message = _(
                "DF-e distribution has never been queried. Configure and run "
                "the first query to start receiving documents."
            )

        search_all_action_id = request.env.ref(
            "l10n_br_fiscal_dfe.action_server_search_all_dfe"
        ).id
        specific_search_action_id = request.env.ref(
            "l10n_br_fiscal_dfe.action_server_specific_search_dfe"
        ).id

        return {
            "html": request.env["ir.qweb"]._render(
                "l10n_br_fiscal_dfe.dfe_document_banner",
                {
                    "company": company,
                    "last_query_str": last_query_str,
                    "nsu_synced": nsu_synced,
                    "pending_import_count": pending_import_count,
                    "today_total": today_total,
                    "today_third_party": today_third_party,
                    "today_own": today_own,
                    "search_all_action_id": search_all_action_id,
                    "specific_search_action_id": specific_search_action_id,
                    "auto_fetch": company.auto_fetch,
                    "next_query_str": next_query_str,
                    "is_homologation": company.dfe_environment == "2",
                    "inactivity_warning": inactivity_warning,
                    "inactivity_message": inactivity_message,
                },
            )
        }
