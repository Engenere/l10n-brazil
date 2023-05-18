# Copyright (C) 2009 - TODAY Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from datetime import datetime, time

from pytz import UTC, timezone

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    DOCUMENT_ISSUER_PARTNER,
    SITUACAO_EDOC_EM_DIGITACAO,
)


class FiscalDocument(models.Model):
    _inherit = "l10n_br_fiscal.document"

    move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="fiscal_document_id",
        string="Invoices",
    )

    fiscal_line_ids = fields.One2many(
        copy=False,
    )

    document_date = fields.Datetime(
        compute="_compute_document_date", inverse="_inverse_document_date", store=True
    )

    @api.depends("move_ids.invoice_date")
    def _compute_document_date(self):
        for record in self:
            if record.move_ids and record.issuer == DOCUMENT_ISSUER_PARTNER:
                move_id = record.move_ids[0]
                if move_id.invoice_date:
                    user_tz = timezone(self.env.user.tz or "UTC")
                    doc_date = datetime.combine(move_id.invoice_date, time.min)
                    record.document_date = (
                        user_tz.localize(doc_date).astimezone(UTC).replace(tzinfo=None)
                    )

    def _inverse_document_date(self):
        for record in self:
            if record.move_ids and record.issuer == DOCUMENT_ISSUER_PARTNER:
                move_id = record.move_ids[0]
                if record.document_date:
                    move_id.invoice_date = record.document_date.date()

    def unlink(self):
        non_draft_documents = self.filtered(
            lambda d: d.state != SITUACAO_EDOC_EM_DIGITACAO
        )

        if non_draft_documents:
            UserError(
                _("You cannot delete a fiscal document " "which is not draft state.")
            )
        return super().unlink()
