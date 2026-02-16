# Copyright 2026 Engenere
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)

# All fields that had compute="_compute_tax_fields" in the original mixin,
# grouped by SQL type for proper jsonb_build_object casting.
# Many2one fields are stored as integer IDs.
# Monetary/Float fields are stored as numeric.
# Selection fields are stored as text.
_MONETARY_FIELDS = [
    "amount_tax_included",
    "amount_tax_not_included",
    "amount_tax_withholding",
    "estimate_tax",
    # ISSQN
    "issqn_base",
    "issqn_value",
    "issqn_wh_base",
    "issqn_wh_value",
    # ICMS
    "icms_base",
    "icms_value",
    "icms_relief_value",
    "icms_destination_base",
    "icms_origin_value",
    "icms_destination_value",
    # ICMS ST
    "icmsst_base",
    "icmsst_value",
    # ICMS FCP
    "icmsfcp_base",
    "icmsfcp_value",
    # ICMS FCP ST
    "icmsfcpst_base",
    "icmsfcpst_value",
    # ICMS SN
    "icmssn_base",
    "icmssn_reduction",
    "icmssn_credit_value",
    # IPI
    "ipi_base",
    "ipi_value",
    # CBS
    "cbs_base",
    "cbs_value",
    # IBS
    "ibs_base",
    "ibs_value",
    # II
    "ii_base",
    "ii_value",
    # COFINS
    "cofins_base",
    "cofins_value",
    # COFINS ST
    "cofinsst_base",
    "cofinsst_value",
    # COFINS WH
    "cofins_wh_base",
    "cofins_wh_value",
    # PIS
    "pis_base",
    "pis_value",
    # PIS ST
    "pisst_base",
    "pisst_value",
    # PIS WH
    "pis_wh_base",
    "pis_wh_value",
    # CSLL
    "csll_base",
    "csll_value",
    # CSLL WH
    "csll_wh_base",
    "csll_wh_value",
    # IRPJ
    "irpj_base",
    "irpj_value",
    # IRPJ WH
    "irpj_wh_base",
    "irpj_wh_value",
    # INSS
    "inss_base",
    "inss_value",
    # INSS WH
    "inss_wh_base",
    "inss_wh_value",
]

_FLOAT_FIELDS = [
    # ISSQN
    "issqn_percent",
    "issqn_reduction",
    "issqn_wh_percent",
    "issqn_wh_reduction",
    # ICMS
    "icms_percent",
    "icms_reduction",
    "icms_origin_percent",
    "icms_destination_percent",
    "icms_sharing_percent",
    # ICMS ST
    "icmsst_mva_percent",
    "icmsst_reduction",
    "icmsst_percent",
    # ICMS FCP
    "icmsfcp_percent",
    # ICMS FCP ST
    "icmsfcpst_percent",
    # ICMS SN
    "icmssn_percent",
    # IPI
    "ipi_percent",
    "ipi_reduction",
    # CBS
    "cbs_percent",
    "cbs_reduction",
    # IBS
    "ibs_percent",
    "ibs_reduction",
    # II
    "ii_percent",
    # COFINS
    "cofins_percent",
    "cofins_reduction",
    # COFINS ST
    "cofinsst_percent",
    "cofinsst_reduction",
    # COFINS WH
    "cofins_wh_percent",
    "cofins_wh_reduction",
    # PIS
    "pis_percent",
    "pis_reduction",
    # PIS ST
    "pisst_percent",
    "pisst_reduction",
    # PIS WH
    "pis_wh_percent",
    "pis_wh_reduction",
    # CSLL
    "csll_percent",
    "csll_reduction",
    # CSLL WH
    "csll_wh_percent",
    "csll_wh_reduction",
    # IRPJ
    "irpj_percent",
    "irpj_reduction",
    # IRPJ WH
    "irpj_wh_percent",
    "irpj_wh_reduction",
    # INSS
    "inss_percent",
    "inss_reduction",
    # INSS WH
    "inss_wh_percent",
    "inss_wh_reduction",
]

_MANY2ONE_FIELDS = [
    "issqn_tax_id",
    "issqn_wh_tax_id",
    "icms_tax_id",
    "icms_cst_id",
    "icmsst_tax_id",
    "icmsfcp_tax_id",
    "icmsfcpst_tax_id",
    "icmssn_tax_id",
    "ipi_tax_id",
    "ipi_cst_id",
    "cbs_tax_id",
    "cbs_cst_id",
    "ibs_tax_id",
    "ibs_cst_id",
    "ii_tax_id",
    "cofins_tax_id",
    "cofins_cst_id",
    "cofinsst_tax_id",
    "cofinsst_cst_id",
    "cofins_wh_tax_id",
    "pis_tax_id",
    "pis_cst_id",
    "pisst_tax_id",
    "pisst_cst_id",
    "pis_wh_tax_id",
    "csll_tax_id",
    "csll_wh_tax_id",
    "irpj_tax_id",
    "irpj_wh_tax_id",
    "inss_tax_id",
    "inss_wh_tax_id",
]

_SELECTION_FIELDS = [
    "icms_base_type",
    "icmsst_base_type",
    "ipi_base_type",
    "cofins_base_type",
    "cofinsst_base_type",
    "cofins_wh_base_type",
    "pis_base_type",
    "pisst_base_type",
    "pis_wh_base_type",
    "cbs_base_type",
    "ibs_base_type",
]

ALL_TAX_DATA_FIELDS = (
    _MONETARY_FIELDS + _FLOAT_FIELDS + _MANY2ONE_FIELDS + _SELECTION_FIELDS
)

# Concrete tables that inherit from the mixin and store these columns.
_TABLES = [
    "l10n_br_fiscal_document_line",
    "sale_order_line",
    "purchase_order_line",
    "account_move_line",
    "stock_move",
]


def _build_jsonb_expr():
    """Build a SQL expression that reads all tax columns and packs them
    into a single JSONB value.

    PostgreSQL limits jsonb_build_object to 100 arguments (50 key-value
    pairs), so we split into chunks and merge with the || operator.
    """
    chunk_size = 40  # 40 fields = 80 args, well under the 100 limit
    chunks = []
    for start in range(0, len(ALL_TAX_DATA_FIELDS), chunk_size):
        batch = ALL_TAX_DATA_FIELDS[start : start + chunk_size]
        pairs = []
        for fname in batch:
            pairs.append(f"'{fname}', {fname}")
        chunks.append("jsonb_build_object(" + ", ".join(pairs) + ")")
    return " || ".join(chunks)


def _pre_init_populate_tax_data(cr):
    """Pre-init hook: add tax_data column and populate it from existing
    individual columns via SQL, so data is preserved when the compute
    method changes."""
    jsonb_expr = _build_jsonb_expr()
    for table in _TABLES:
        # Check if the table exists (module may not be installed)
        cr.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = %s AND table_schema = 'public'",
            (table,),
        )
        if not cr.fetchone():
            _logger.info("l10n_br_fiscal_tax_json: table %s not found, skipping", table)
            continue

        # Check if at least one of the source columns exists
        cr.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = 'icms_value'",
            (table,),
        )
        if not cr.fetchone():
            _logger.info(
                "l10n_br_fiscal_tax_json: table %s has no fiscal columns, " "skipping",
                table,
            )
            continue

        # Add the column if it doesn't exist yet
        # pylint: disable=sql-injection
        cr.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tax_data jsonb")

        # Populate from existing columns
        _logger.info("l10n_br_fiscal_tax_json: populating tax_data on %s", table)
        # pylint: disable=sql-injection
        cr.execute(f"UPDATE {table} SET tax_data = {jsonb_expr} WHERE tax_data IS NULL")
        _logger.info(
            "l10n_br_fiscal_tax_json: populated %d rows on %s",
            cr.rowcount,
            table,
        )
