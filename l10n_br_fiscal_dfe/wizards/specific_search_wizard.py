# Copyright 2026 Engenere (<https://engenere.one>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from erpbrasil.base.fiscal.edoc import ChaveEdoc

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DFeSpecificSearchWizard(models.TransientModel):
    _name = "dfe_specific_search_wizard"
    _description = "Wizard to search specific DFe"

    access_key = fields.Char(
        help="Access Key of the electronic fiscal document to be searched.",
    )

    nsu = fields.Char(
        string="NSU",
        help=(
            "NSU (Numero Sequencial Unico) is a unique sequential number assigned to "
            "each document in the Brazilian electronic fiscal document system."
        ),
    )

    search_type = fields.Selection(
        selection=[
            ("access_key", "Search by Access Key"),
            ("nsu", "Search by NSU"),
        ],
        default="access_key",
        required=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company.id,
    )

    @api.onchange("access_key")
    def _onchange_access_key(self):
        if self.access_key:
            self.access_key = re.sub(r"[^0-9]", "", self.access_key)

    @staticmethod
    def _sanitize_access_key(raw_key):
        """Strip non-digit characters from the access key."""
        return re.sub(r"[^0-9]", "", raw_key or "")

    @staticmethod
    def _validate_access_key(key):
        """Validate access key using ChaveEdoc (format + check digit)."""
        if not key:
            raise UserError(_("Please enter an access key."))
        try:
            ChaveEdoc(chave=key, validar=True)
        except ValueError as exc:
            raise UserError(str(exc)) from exc

    def action_confirm_search(self):
        self.ensure_one()
        if self.search_type == "access_key":
            access_key = self._sanitize_access_key(self.access_key)
            self._validate_access_key(access_key)
            self.company_id._dfe_search_specific_document(access_key=access_key)
        else:
            self.company_id._dfe_search_specific_document(nsu=self.nsu)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Specific search triggered successfully"),
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }
