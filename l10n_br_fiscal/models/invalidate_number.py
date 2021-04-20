# Copyright (C) 2009 - TODAY Renato Lima - Akretion
# Copyright (C) 2014  KMEE - www.kmee.com.br
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo.exceptions import UserError, ValidationError

from odoo import _, api, fields, models
from ..constants.fiscal import SITUACAO_EDOC_INUTILIZADA


class InvalidateNumber(models.Model):
    _name = 'l10n_br_fiscal.invalidate.number'
    _description = 'Invalidate Number'

    date = fields.Date(
        string='Date',
        default=fields.Date.today,
        readonly=True,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        readonly=True,
        default=lambda self: self.env.user.company_id.id,
        required=True,
        states={'draft': [('readonly', False)]},
    )

    document_type_id = fields.Many2one(
        comodel_name='l10n_br_fiscal.document.type',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    document_electronic = fields.Boolean(
        related='document_type_id.electronic',
        string='Electronic?',
        readonly=True)

    document_serie_id = fields.Many2one(
        comodel_name='l10n_br_fiscal.document.serie',
        domain="""[('active', '=', True),
            ('document_type_id', '=', document_type_id),
            ('company_id', '=', company_id)]""",
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    number_start = fields.Integer(
        string='Initial Number',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    number_end = fields.Integer(
        string='End Number',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    justification = fields.Char(
        string='Justification',
        size=255,
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    state = fields.Selection(
        selection=[
            ('draft', _('Draft')),
            ('done', _('Done')),
        ],
        string='Status',
        readonly=True,
        default='draft',
    )

    event_ids = fields.One2many(
        comodel_name='l10n_br_fiscal.event',
        inverse_name='invalidate_number_id',
        string='Events',
        readonly=True,
        states={'done': [('readonly', True)]},
    )

    @api.multi
    @api.constrains('number_start', 'number_end')
    def _check_range(self):
        for record in self:
            if record.company_id:
                domain = [
                    ('id', '!=', record.id),
                    ('state', '=', 'done'),
                    ('document_serie_id', '=', record.document_serie_id.id),
                    '|',
                    ('number_end', '>=', record.number_end),
                    ('number_end', '=', False),
                    '|',
                    ('number_start', '<=', record.number_start),
                    ('number_start', '=', False)]

                if self.search_count(domain):
                    raise ValidationError(
                        _('Number range overlap is not allowed.'))
        return True

    @api.multi
    def name_get(self):
        return [(rec.id,
                 '({0}): {1} - {2}'.format(
                     rec.document_serie_id.name,
                     rec.number_start,
                     rec.number_end)
                 ) for rec in self]

    @api.multi
    def unlink(self):
        if self.filtered(lambda n: not n.state == 'draft'):
            raise UserError(
                _('You can delete only draft Invalidate Number Range !'))
        return super().unlink()

    @api.multi
    def action_invalidate(self):
        for record in self:
            record._invalidate()

    def _update_document_status(self, document_id=None):
        if document_id:
            document_id.state_edoc = SITUACAO_EDOC_INUTILIZADA
        else:
            for number in range(self.number_start, self.number_end + 1):
                self.env['l10n_br_fiscal.document'].create({
                    'document_serie_id': self.document_serie_id.id,
                    'document_type_id':
                        self.document_serie_id.document_type_id.id,
                    'company_id': self.company_id.id,
                    'state_edoc': SITUACAO_EDOC_INUTILIZADA,
                    'issuer': 'company',
                    'number': str(number),
                })

    def _invalidate(self, document_id=None):
        self.ensure_one()
        self._update_document_status(document_id)
        self.state = 'done'
