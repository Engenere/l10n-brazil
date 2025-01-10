from odoo import _, fields, models


class MdeWizard(models.TransientModel):
    _name = "mde.wizard"
    _description = "Wizard para Criar MDe"

    state = fields.Selection(
        selection=[
            ("pendente", "Pendente"),
            ("ciente", "Ciente"),
            ("confirmado", "Confirmada operação"),
            ("desconhecido", "Desconhecimento"),
            ("nao_realizado", "Não realizado"),
        ],
        default="pendente",
        required=True,
    )

    def action_create_mde(self):
        dfe_id = self.env.context.get("default_dfe_id")
        dfe_record = self.env["l10n_br_fiscal.dfe"].browse(dfe_id)

        self.env["l10n_br_nfe.mde"].create(
            {
                "key": dfe_record.key,
                "state": self.state,
                "company_id": dfe_record.company_id.id,
                "dfe_id": dfe_record.id,
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sucesso"),
                "message": _("MDe criado com sucesso"),
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
