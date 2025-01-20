from odoo import fields, models

from ..constants.dfe import (
    OPERATION_TYPE,
    SITUACAO_NFE,
)


class DFe(models.Model):
    _name = "l10n_br_fiscal.dfe"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Consult DF-e"

    key = fields.Char(string="Access Key", size=44)

    serie = fields.Char(size=3, index=True)

    number = fields.Float(string="Document Number", index=True, digits=(18, 0))

    emitter = fields.Char(size=60)

    cnpj_cpf = fields.Char(string="CNPJ/CPF", size=18)

    nsu = fields.Char(string="NSU", size=25, index=True)

    operation_type = fields.Selection(
        selection=OPERATION_TYPE,
    )

    document_value = fields.Float(
        string="Document Total Value",
        readonly=True,
        digits=(18, 2),
    )

    ie = fields.Char(string="Inscrição estadual", size=18)

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Supplier (partner)",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
    )

    emission_datetime = fields.Datetime(
        string="Emission Date",
        index=True,
        default=fields.Datetime.now,
    )

    inclusion_datetime = fields.Datetime(
        string="Inclusion Date",
        index=True,
        default=fields.Datetime.now,
    )

    inclusion_mode = fields.Char(size=255)

    document_state = fields.Selection(
        selection=SITUACAO_NFE,
        index=True,
    )

    cfop_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.cfop",
        string="CFOPs",
    )

    dfe_nfe_document_type = fields.Selection(
        selection=[
            ("dfe_nfe_complete", "NF-e Completa"),
            ("dfe_nfe_summary", "Resumo da NF-e"),
            ("dfe_nfe_event", "Evento da NF-e"),
        ],
        string="DFe Document Type",
    )

    dfe_monitor_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.dfe_monitor",
        string="DFe Monitor",
    )

    def name_get(self):
        return [
            (
                rec.id,
                f"NFº: {rec.number} ({rec.cnpj_cpf})",
            )
            for rec in self
        ]
