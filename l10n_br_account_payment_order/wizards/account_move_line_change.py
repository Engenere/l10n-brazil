# Copyright 2020 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveLineChange(models.TransientModel):
    _name = 'account.move.line.change'
    _description = 'Wizard de edição de pagamento'

    @api.model
    def default_get(self, fields_list):
        res = super(AccountMoveLineChange, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'account.move.line':
            active_ids = self.env.context.get('active_ids')
            res['account_move_line_ids'] = active_ids
            if active_ids and len(active_ids) == 1:
                move_line_id = self.account_move_line_ids.browse(
                    active_ids
                )
                if move_line_id.date_maturity:
                    res['date_maturity'] = move_line_id.date_maturity
                if move_line_id.payment_mode_id:
                    res['payment_mode_id'] = move_line_id.payment_mode_id.id
        return res

    account_move_line_ids = fields.Many2many(
        comodel_name='account.move.line',
        string='Move Line',
        readonly=True,
    )
    change_type = fields.Selection(
        selection=[
            ('change_date_maturity', 'Vencimento'),
            # TODO: É preciso mais detalhes dessa operação ao enviar fora o
            #  codigo de alteração e carteira o que mais deve ir ?
            #  Ao alterar a carteira/payment mode de um Título deveria ser
            #  alterada de todas as account.move.line dessa invoice ?
            # ('change_payment_mode', 'Modo de Pagamento'),
            # TODO: qual seria esse caso Baixa ? Já que em caso de pagamento
            #  por fora do CNAB é preciso registrar o pagamento e isso está
            #  sendo chamado no metodo post do account.payment .
            # ('baixa', 'Baixa'),
            ('not_payment', 'Baixa por Não Pagamento/Inadimplência'),
            ('protest_tittle', 'Protestar Titulo'),
        ],
        string='Tipo Alteração',
    )
    date_maturity = fields.Date(
        string="Date Maturity"
    )
    payment_mode_id = fields.Many2one(
        comodel_name='account.payment.mode',
    )
    reason = fields.Text(
        string="Justificativa",
    )
    # Muitas opções são permitidas, verificar manual do cnab 240.
    # Entretanto inicialmente só vamos implementar as mais simples.

    @api.multi
    def doit(self):
        self.account_move_line_ids._create_change(
            change_type=self.change_type,
            reason=self.reason,
            new_date=self.date_maturity,
            new_payment_mode_id=self.payment_mode_id,
        )
