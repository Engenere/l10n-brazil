# Copyright 2026 Engenere - Felipe Motter Pereira
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
"""See pre-migration.py. Step 3 comes from Antônio Neto's review of OCA PR #4416."""

from openupgradelib import openupgrade
from psycopg2 import sql

TABLES = [
    "l10n_br_fiscal_dfe_document",
    "l10n_br_fiscal_dfe_dfe",
    "l10n_br_fiscal_dfe_distribution_log",
]


def migrate(cr, version):
    # 3. fiscal_type is new: without a value the documents fetched before this
    #    version disappear from the views filtered by type. The unofficial
    #    implementation only distributed NF-e.
    for table in TABLES:
        openupgrade.logged_query(
            cr,
            sql.SQL(
                "UPDATE {} SET fiscal_type = 'nfe' "
                "WHERE fiscal_type IS NULL OR fiscal_type = ''"
            ).format(sql.Identifier(table)),
        )
