from odoo import fields, models


class NfeRecipientManifestationEvent(models.Model):
    _inherit = "l10n_br_nfe.md_event"

    dfe_document_id = fields.Many2one(
        string="Fiscal Document", comodel_name="l10n_br_fiscal_dfe.document"
    )
