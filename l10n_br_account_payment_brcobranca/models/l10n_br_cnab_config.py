# Copyright (C) 2024-Today - Akretion (<http://www.akretion.com>).
# @author Magno Costa <magno.costa@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


class L10nBRCNABConfig(models.Model):
    """
    Override CNAB Config
    """

    _inherit = "l10n_br_cnab.config"

    @api.model
    def _selection_cnab_processor(self):
        selection = super()._selection_cnab_processor()
        selection.append(("brcobranca", "BRCobrança"))
        return selection

    brcobranca_modelo = fields.Selection(
        selection=[
            ("rghost", "Padrão 1"),
            ("rghost2", "Padrão 2"),
            ("rghost_carne", "Carne"),
        ],
        string="Modelo do Boleto",
        help="Modelo para impressão do Boleto",
        default="rghost",
    )

