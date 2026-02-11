# Copyright 2026 Engenere (<https://engenere.one>).
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, http
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

        last_query = company.dfe_last_query
        if last_query:
            user_tz = request.env.user.tz or "UTC"
            last_query_str = last_query.astimezone(
                __import__("pytz").timezone(user_tz)
            ).strftime("%d/%m/%Y %H:%M")
        else:
            last_query_str = "-"

        nsu_synced = (
            company.last_nsu and company.max_nsu and company.last_nsu >= company.max_nsu
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
                },
            )
        }
