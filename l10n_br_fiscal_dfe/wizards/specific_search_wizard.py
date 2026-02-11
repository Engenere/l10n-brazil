# Copyright 2026 Engenere (<https://engenere.one>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


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

    def action_confirm_search(self):
        self.ensure_one()
        self.company_id._dfe_search_specific_document(
            access_key=self.access_key, nsu=self.nsu
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Specific search triggered successfully"),
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
