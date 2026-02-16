# Copyright 2026 Engenere
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _setup_complete(self):
        """Extend l10n_br_purchase's _setup_complete to also disable precompute
        for the new compute methods introduced by l10n_br_fiscal_tax_json.

        The original l10n_br_purchase disables precompute for fields whose
        compute is in a specific list (including "_compute_tax_fields").
        After our module rewires those fields to "_compute_from_tax_data",
        they would no longer be caught. We also need to handle
        "_compute_tax_data" itself.
        """
        res = super()._setup_complete()
        mixin = self.env["l10n_br_fiscal.document.line.mixin"]
        mixin_fields = mixin._fields
        for name, field in self._fields.items():
            mixin_field = mixin_fields.get(name)
            if not mixin_field:
                continue
            if mixin_field.compute in (
                "_compute_from_tax_data",
                "_compute_tax_data",
            ) and getattr(mixin_field, "precompute", False):
                field.precompute = False
        return res
