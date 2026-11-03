# Copyright 2026 Engenere - Felipe Motter Pereira
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
"""Migrate databases that ran the unofficial DF-e distribution (OCA PR #4383).

That implementation shipped l10n_br_fiscal_dfe 16.0.1.4.0 with the NF-e specifics
inside it. The official module (OCA PR #4416) is generic and moved them to
l10n_br_nfe_dfe, which must be installed in the same run as this update.
Steps 1 to 3 come from Antônio Neto's review of OCA PR #4416.
"""

from openupgradelib import openupgrade

from odoo.exceptions import UserError

# The DF-e monitor fields of the company moved to l10n_br_nfe_dfe with the nfe_
# prefix: without renaming, _process_end drops the old columns and the last NSU
# is lost, so the next query restarts the distribution from zero.
COMPANY_COLUMNS = [
    ("last_nsu", "nfe_last_nsu"),
    ("max_nsu", "nfe_max_nsu"),
    ("dfe_last_query", "nfe_dfe_last_query"),
    ("dfe_last_status", "nfe_dfe_last_status"),
    ("dfe_last_status_code", "nfe_dfe_last_status_code"),
    ("dfe_next_query", "nfe_dfe_next_query"),
    ("auto_fetch", "nfe_auto_fetch"),
    ("dfe_version", "nfe_dfe_version"),
]


def _check_dfe_environment(cr):
    """The unofficial fork had its own dfe_environment; the official module
    queries the SEFAZ with nfe_environment, the one used to issue NF-e.

    Stop instead of silently switching the DF-e environment of a company.
    """
    if not (
        openupgrade.column_exists(cr, "res_company", "dfe_environment")
        and openupgrade.column_exists(cr, "res_company", "nfe_environment")
    ):
        return
    openupgrade.logged_query(
        cr,
        """
        SELECT id, name, dfe_environment, nfe_environment
          FROM res_company
         WHERE dfe_environment IS NOT NULL
           AND dfe_environment IS DISTINCT FROM nfe_environment
        """,
    )
    divergent = cr.fetchall()
    if divergent:
        raise UserError(
            "The DF-e now queries the SEFAZ with the NF-e environment, but these "
            "companies have a different DF-e environment (id, name, DF-e, NF-e): "
            f"{divergent}. Align the environments before updating."
        )


def migrate(cr, version):
    _check_dfe_environment(cr)
    company_renames = [
        (old_name, new_name)
        for old_name, new_name in COMPANY_COLUMNS
        if openupgrade.column_exists(cr, "res_company", old_name)
        and not openupgrade.column_exists(cr, "res_company", new_name)
    ]
    if company_renames:
        openupgrade.rename_columns(cr, {"res_company": company_renames})

    # 1. document_state became a Char: the orphan metadata of the old Selection
    #    breaks ir.model._process_ondelete during the update.
    openupgrade.logged_query(
        cr,
        """
        DELETE FROM ir_model_fields_selection
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE model = 'ir.model.fields.selection'
              AND module = 'l10n_br_fiscal_dfe'
              AND name LIKE 'selection__l10n_br_fiscal_dfe_document__document_state__%'
        )
        """,
    )
    openupgrade.logged_query(
        cr,
        """
        DELETE FROM ir_model_data
        WHERE model = 'ir.model.fields.selection'
          AND module = 'l10n_br_fiscal_dfe'
          AND name LIKE 'selection__l10n_br_fiscal_dfe_document__document_state__%'
        """,
    )

    # 2. dfe_nfe_document_type became document_type_dfe, with new values:
    #    without them no complete XML is found for the documents already fetched.
    if openupgrade.column_exists(cr, "l10n_br_fiscal_dfe_dfe", "dfe_nfe_document_type"):
        openupgrade.rename_columns(
            cr,
            {
                "l10n_br_fiscal_dfe_dfe": [
                    ("dfe_nfe_document_type", "document_type_dfe")
                ]
            },
        )
        # map_values() refuses a source column equal to the target one: it only
        # logs an error and converts nothing, hence the explicit UPDATE.
        openupgrade.logged_query(
            cr,
            """
            UPDATE l10n_br_fiscal_dfe_dfe
               SET document_type_dfe = CASE document_type_dfe
                   WHEN 'dfe_nfe_complete' THEN 'complete'
                   WHEN 'dfe_nfe_summary' THEN 'summary'
                   WHEN 'dfe_nfe_event' THEN 'event'
               END
             WHERE document_type_dfe IN
                   ('dfe_nfe_complete', 'dfe_nfe_summary', 'dfe_nfe_event')
            """,
        )
