# Copyright 2026 Engenere
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    TAX_BASE_TYPE_PERCENT,
)
from odoo.addons.l10n_br_fiscal.constants.icms import (
    ICMS_BASE_TYPE_DEFAULT,
    ICMS_ST_BASE_TYPE_DEFAULT,
)

_logger = logging.getLogger(__name__)


class FiscalDocumentLineMixin(models.AbstractModel):
    _inherit = "l10n_br_fiscal.document.line.mixin"

    tax_data = fields.Json(
        string="Tax Computation Data",
        compute="_compute_tax_data",
        store=True,
        readonly=False,
    )

    @api.depends(
        "partner_id",
        "fiscal_tax_ids",
        "product_id",
        "price_unit",
        "quantity",
        "uom_id",
        "fiscal_price",
        "fiscal_quantity",
        "uot_id",
        "discount_value",
        "insurance_value",
        "ii_customhouse_charges",
        "ii_iof_value",
        "other_value",
        "freight_value",
        "ncm_id",
        "nbs_id",
        "nbm_id",
        "cest_id",
        "fiscal_operation_line_id",
        "cfop_id",
        "icmssn_range_id",
        "icms_origin",
        "ind_final",
        "icms_relief_id",
    )
    def _compute_tax_data(self):
        null_mask = None
        for line in self.filtered(lambda line: not line._is_imported()):
            if null_mask is None:
                null_mask = self._build_null_mask_dict()
            to_update = null_mask.copy()
            to_update.update(
                {
                    "icms_base_type": ICMS_BASE_TYPE_DEFAULT,
                    "icmsst_base_type": ICMS_ST_BASE_TYPE_DEFAULT,
                    "ipi_base_type": TAX_BASE_TYPE_PERCENT,
                    "cofins_base_type": TAX_BASE_TYPE_PERCENT,
                    "cofinsst_base_type": TAX_BASE_TYPE_PERCENT,
                    "cofins_wh_base_type": TAX_BASE_TYPE_PERCENT,
                    "pis_base_type": TAX_BASE_TYPE_PERCENT,
                    "pisst_base_type": TAX_BASE_TYPE_PERCENT,
                    "pis_wh_base_type": TAX_BASE_TYPE_PERCENT,
                    "cbs_base_type": TAX_BASE_TYPE_PERCENT,
                    "ibs_base_type": TAX_BASE_TYPE_PERCENT,
                }
            )
            if line.fiscal_operation_line_id:
                compute_result = line.fiscal_tax_ids.compute_taxes(
                    company=line.company_id,
                    partner=line._get_fiscal_partner(),
                    product=line.product_id,
                    price_unit=line.price_unit,
                    quantity=line.quantity,
                    uom_id=line.uom_id,
                    fiscal_price=line.fiscal_price,
                    fiscal_quantity=line.fiscal_quantity,
                    uot_id=line.uot_id,
                    discount_value=line.discount_value,
                    insurance_value=line.insurance_value,
                    ii_customhouse_charges=line.ii_customhouse_charges,
                    ii_iof_value=line.ii_iof_value,
                    other_value=line.other_value,
                    freight_value=line.freight_value,
                    ncm=line.ncm_id,
                    nbs=line.nbs_id,
                    nbm=line.nbm_id,
                    cest=line.cest_id,
                    operation_line=line.fiscal_operation_line_id,
                    cfop=line.cfop_id,
                    icmssn_range=line.icmssn_range_id,
                    icms_origin=line.icms_origin,
                    ind_final=line.ind_final,
                    icms_relief_id=line.icms_relief_id,
                )
                to_update.update(line._prepare_tax_fields(compute_result))
            else:
                compute_result = {}
            to_update.update(
                {
                    "amount_tax_included": compute_result.get("amount_included", 0.0),
                    "amount_tax_not_included": compute_result.get(
                        "amount_not_included", 0.0
                    ),
                    "amount_tax_withholding": compute_result.get(
                        "amount_withholding", 0.0
                    ),
                    "estimate_tax": compute_result.get("estimate_tax", 0.0),
                }
            )
            # Convert recordset IDs for Many2one fields to plain integers
            # so the dict is JSON-serializable.
            for key, val in to_update.items():
                if hasattr(val, "id"):
                    to_update[key] = val.id
            line.tax_data = to_update

    @api.depends("tax_data")
    def _compute_from_tax_data(self):
        for line in self:
            data = line.tax_data or {}
            for fname in self._tax_data_field_names:
                line[fname] = data.get(fname, False)

    @api.model
    def inject_fiscal_fields(self, doc, view_ref=None, xpath_mappings=None):
        """Override to include '_compute_from_tax_data' in the set of
        computed fields that should be injected into views.

        The original method only checks for '_compute_tax_fields', but after
        our rewiring those fields have compute='_compute_from_tax_data'.
        We temporarily set them back so super() finds them, then restore.
        """
        mixin_fields = self.env["l10n_br_fiscal.document.line.mixin"]._fields
        patched = []
        for fname, field_obj in mixin_fields.items():
            if getattr(field_obj, "compute", None) == "_compute_from_tax_data":
                field_obj.compute = "_compute_tax_fields"
                patched.append((fname, field_obj))
        try:
            kwargs = {}
            if view_ref is not None:
                kwargs["view_ref"] = view_ref
            if xpath_mappings is not None:
                kwargs["xpath_mappings"] = xpath_mappings
            result = super().inject_fiscal_fields(doc, **kwargs)
        finally:
            for _fname, field_obj in patched:
                field_obj.compute = "_compute_from_tax_data"
        return result

    @api.model
    def _build_null_mask_dict(self) -> dict:
        """Override to filter by the new compute method name."""
        mask_dict = {
            fname: False
            for fname, field_obj in self.env[
                "l10n_br_fiscal.document.line.mixin"
            ]._fields.items()
            if field_obj.compute == "_compute_from_tax_data"
        }
        from odoo.addons.l10n_br_fiscal.constants.fiscal import (
            FISCAL_TAX_ID_FIELDS,
        )

        for fiscal_tax_field in FISCAL_TAX_ID_FIELDS:
            mask_dict[fiscal_tax_field] = False
        return mask_dict

    def _setup_complete(self):
        res = super()._setup_complete()
        cls = type(self)
        target_fields = []
        rewired = 0
        for fname, field_obj in cls._fields.items():
            if getattr(field_obj, "compute", None) == "_compute_tax_fields":
                field_obj.compute = "_compute_from_tax_data"
                field_obj.depends = ("tax_data",)
                field_obj.precompute = False
                target_fields.append(fname)
                rewired += 1
            elif getattr(field_obj, "compute", None) == "_compute_from_tax_data":
                # Already rewired (e.g. by the abstract model's _setup_complete
                # on a shared field object) — still collect it.
                target_fields.append(fname)
        cls._tax_data_field_names = tuple(target_fields)
        if rewired:
            _logger.debug(
                "l10n_br_fiscal_tax_json: rewired %d fields to "
                "_compute_from_tax_data on %s",
                rewired,
                cls._name,
            )
        return res
