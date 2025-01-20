from odoo import _, fields, models


class DFe(models.Model):
    _inherit = "l10n_br_fiscal.dfe"

    mde_ids = fields.One2many(
        comodel_name="l10n_br_nfe.mde",
        inverse_name="dfe_id",
        string="Manifestações do Destinatário Importadas",
    )

    def create_mde_action(self):
        return {
            "name": _("Manifestar MDe"),
            "type": "ir.actions.act_window",
            "res_model": "mde.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_dfe_id": self.id,
            },
        }

    def import_document_multi(self):
        # TODO Vê esse método
        pass
