#    Copyright (C) 2016 MultidadosTI (http://www.multidadosti.com.br)
#    @author Michell Stuttgart <michellstut@gmail.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models
from odoo.osv import expression


class ResBank(models.Model):
    _inherit = "res.bank"

    short_name = fields.Char()

    code_bc = fields.Char(
        string="Brazilian Bank Code",
        size=3,
        help="Brazilian Bank Code ex.: 001 is the code of Banco do Brasil",
        unaccent=False,
    )

    ispb_number = fields.Char(
        string="ISPB Number",
        size=8,
        unaccent=False,
    )

    compe_member = fields.Boolean(
        string="COMPE Member",
        default=False,
    )

    @api.model
    def name_get(self):
        """
        Override name_get to include the Brazilian bank code in the name
        if the context variable 'show_l10n_br_bank_code' is set to True.
        Example: 001 - Banco do Brasil
        """
        if not self.env.context.get("show_l10n_br_bank_code"):
            return super().name_get()

        result = []
        for bank in self:
            name = bank.name
            if bank.code_bc:
                name = f"{bank.code_bc} - {name}"
            result.append((bank.id, name))
        return result

    @api.model
    def _name_search(
        self,
        name,
        args=None,
        operator="ilike",
        limit=100,
        name_get_uid=None,
    ):
        """
        Allow searching by BIC, name or COMPE (code_bc).
        """
        args = args or []
        bank_ids = list(
            super()._name_search(
                name,
                args=args,
                operator=operator,
                limit=limit,
                name_get_uid=name_get_uid,
            )
        )
        if not name or len(bank_ids) >= limit:
            return bank_ids

        remaining = limit - len(bank_ids)
        code_domain = (
            [("code_bc", operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS
            else [("code_bc", "=ilike", f"{name}%")]
        )
        code_domain = expression.AND([code_domain, [("id", "not in", bank_ids)]])

        extra_ids = self._search(
            code_domain + args,
            limit=remaining,
            access_rights_uid=name_get_uid,
        )
        return bank_ids + list(extra_ids)
