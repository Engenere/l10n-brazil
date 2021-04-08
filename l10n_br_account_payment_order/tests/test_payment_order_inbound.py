# @ 2020 Akretion - www.akretion.com.br -
#   Magno Costa <magno.costa@akretion.com.br>
# @ 2020 KMEE - www.kmee.com.br
#   Luis Felipe Mileo <mileo@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import time

from odoo.tests import tagged
from odoo.tests import SavepointCase
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestPaymentOrderInbound(SavepointCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.register_payments_model = \
            self.env['account.register.payments'].with_context(
                active_model='account.invoice')
        self.payment_model = self.env['account.payment']

        # Get Invoice for test
        self.invoice_cef = self.env.ref(
            'l10n_br_account_payment_order.'
            'demo_invoice_payment_order_cef_cnab240'
        )
        self.invoice_unicred = self.env.ref(
            'l10n_br_account_payment_order.'
            'demo_invoice_payment_order_unicred_cnab400'
        )

        # Journal
        self.journal_cash = self.env[
            'account.journal'].search([('type', '=', 'cash')], limit=1)
        self.payment_method_manual_in = \
            self.env.ref('account.account_payment_method_manual_in')

    def test_create_payment_order(self):
        """ Test Create Payment Order """

        # I check that Initially customer invoice is in the "Draft" state
        self.assertEquals(self.invoice_cef.state, 'draft')

        # I validate invoice by creating on
        self.invoice_cef.action_invoice_open()

        # I check that the invoice state is "Open"
        self.assertEquals(self.invoice_cef.state, 'open')

        # I check that now there is a move attached to the invoice
        assert self.invoice_cef.move_id, \
            "Move not created for open invoice"

        payment_order = self.env['account.payment.order'].search([
            ('payment_mode_id', '=', self.invoice_cef.payment_mode_id.id)
        ])

        assert payment_order, "Payment Order not created."

        # TODO: Caso CNAB pode cancelar o Move ?
        #  Aparetemente isso precisa ser validado
        # Change status of Move to draft just to test
        self.invoice_cef.move_id.button_cancel()

        for line in self.invoice_cef.move_id.line_ids.filtered(
                lambda l: l.account_id.id == self.invoice_cef.account_id.id):
            self.assertEquals(
                line.journal_entry_ref, line.invoice_id.name,
                "Error with compute field journal_entry_ref")

        # Return the status of Move to Posted
        self.invoice_cef.move_id.action_post()

        # Verificar os campos CNAB na account.move.line
        for line in self.invoice_cef.move_id.line_ids.filtered(
                lambda l: l.account_id.id == self.invoice_cef.account_id.id):
            assert line.own_number, \
                'own_number field is not filled in created Move Line.'
            assert line.mov_instruction_code_id, \
                'mov_instruction_code_id field is not filled' \
                ' in created Move Line.'
            self.assertEquals(
                line.journal_entry_ref, line.invoice_id.name,
                'Error with compute field journal_entry_ref')
            # testar com a parcela 700
            if line.debit == 700.0:
                test_balance_value = line.get_balance()

        self.assertEquals(
            test_balance_value, 700.0,
            'Error with method get_balance()')

        payment_order = self.env['account.payment.order'].search([
            ('payment_mode_id', '=', self.invoice_cef.payment_mode_id.id)
        ])

        # Verifica os campos CNAB na linhas de pagamentos
        for l in payment_order.payment_line_ids:
            assert l.own_number, \
                'own_number field is not filled in Payment Line.'
            assert l.mov_instruction_code_id, \
                'mov_instruction_code_id field are not filled in Payment Line.'

        # Ordem de Pagto CNAB não pode ser apagada
        with self.assertRaises(UserError):
            payment_order.unlink()

        # Open payment order
        payment_order.draft2open()

        # Criação da Bank Line
        self.assertEquals(len(payment_order.bank_line_ids), 2)

        # A geração do arquivo é feita pelo modulo que implementa a
        # biblioteca a ser usada
        # Generate and upload
        # payment_order.open2generated()
        # payment_order.generated2uploaded()

        self.assertEquals(payment_order.state, 'open')

        # Verifica os campos CNAB na linhas de bancarias
        for l in payment_order.bank_line_ids:
            assert l.own_number, \
                'own_number field is not filled in Payment Line.'
            assert l.mov_instruction_code_id, \
                'mov_instruction_code_id field are not filled in Payment Line.'

        # Ordem de Pagto CNAB não pode ser Cancelada
        with self.assertRaises(UserError):
            payment_order.action_done_cancel()

        # Testar Cancelamento
        self.invoice_cef.action_invoice_cancel()

    def test_payment_outside_cnab_payment_order_draft(self):
        """
         Caso de Pagamento ser feito quando a Ordem de Pagamento em Draft deve
         apagar as linhas de pagamentos.
        """
        # I validate invoice by creating on
        self.invoice_unicred.action_invoice_open()

        payment_order = self.env['account.payment.order'].search([
            ('payment_mode_id', '=', self.invoice_unicred.payment_mode_id.id)
        ])
        self.assertEqual(len(payment_order.payment_line_ids), 2)

        ctx = {
            'active_model': 'account.invoice',
            'active_ids': [self.invoice_unicred.id]
        }
        register_payments = \
            self.register_payments_model.with_context(ctx).create({
                'payment_date': time.strftime('%Y') + '-07-15',
                'journal_id': self.journal_cash.id,
                'payment_method_id': self.payment_method_manual_in.id,
            })

        # Caso a Ordem de Pagamento ainda não esteja Confirmada
        register_payments.create_payments()
        payment = self.payment_model.search([], order="id desc", limit=1)

        self.assertAlmostEquals(payment.amount, 1000)
        self.assertEqual(payment.state, 'posted')
        self.assertEqual(self.invoice_unicred.state, 'paid')
        # Linhas Apagadas
        self.assertEqual(len(payment_order.payment_line_ids), 0)

    def test_payment_outside_cnab_payment_order_open(self):
        """
         Caso de Pagamento ser feito quando a Ordem de Pagamento em Open deve
         gerar erro por ter uma Instrução CNAB a ser enviada.
        """
        # I validate invoice by creating on
        self.invoice_unicred.action_invoice_open()

        payment_order = self.env['account.payment.order'].search([
            ('payment_mode_id', '=', self.invoice_unicred.payment_mode_id.id)
        ])
        # Open payment order
        payment_order.draft2open()
        self.assertEqual(payment_order.state, 'open')

        ctx = {
            'active_model': 'account.invoice',
            'active_ids': [self.invoice_unicred.id]
        }
        register_payments = \
            self.register_payments_model.with_context(ctx).create({
                'payment_date': time.strftime('%Y') + '-07-15',
                'journal_id': self.journal_cash.id,
                'payment_method_id': self.payment_method_manual_in.id,
            })

        # Erro de ter uma Instrução CNAB Pendente, como não é possivel gerar a
        # Ordem de Pagto o teste de crição de Write Off e Alteração do Valor do
        # Titulo no caso de um pagamento parcial precisa ser feito no modulo
        # que implementa biblioteca a ser usada.
        with self.assertRaises(UserError):
            register_payments.create_payments()

    def test_cancel_invoice_payment_order_draft(self):
        """ Test Cancel Invoice when Payment Order Draft."""

        # I validate invoice by creating on
        self.invoice_unicred.action_invoice_open()
        payment_order = self.env['account.payment.order'].search([
            ('payment_mode_id', '=', self.invoice_unicred.payment_mode_id.id)
        ])
        self.assertEquals(len(payment_order.payment_line_ids), 2)

        # Testar Cancelamento
        self.invoice_unicred.action_invoice_cancel()

        self.assertEquals(len(payment_order.payment_line_ids), 0)
        # Nesse caso a account.move deverá ter sido apagada
        self.assertEquals(len(self.invoice_unicred.move_id), 0)

    def test_payment_by_assign_outstanding_credit(self):
        """
         Caso de Pagamento com CNAB usando o assign_outstanding_credit
        """
        self.partner_akretion = self.env.ref(
            'l10n_br_base.res_partner_akretion'
        )
        # I validate invoice by creating on
        self.invoice_cef.action_invoice_open()

        payment_order = self.env['account.payment.order'].search([
            ('payment_mode_id', '=', self.invoice_cef.payment_mode_id.id)
        ])
        # Open payment order
        payment_order.draft2open()
        # Generate and upload
        # payment_order.open2generated()
        # payment_order.generated2uploaded()
        # self.assertEquals(payment_order.state, 'done')

        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref(
                'account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_akretion.id,
            'amount': 100,
            'journal_id': self.journal_cash.id,
        })
        payment.post()
        credit_aml = payment.move_line_ids.filtered('credit')

        # Erro de ter uma Instrução CNAB Pendente, como não é possivel gerar a
        # Ordem de Pagto o teste completo de pagamento via
        # assign_outstanding_credit precisa ser feito no modulo que
        # implementa biblioteca a ser usada.
        with self.assertRaises(UserError):
            self.invoice_cef.assign_outstanding_credit(credit_aml.id)
