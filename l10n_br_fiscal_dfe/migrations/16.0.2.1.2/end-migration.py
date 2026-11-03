# Copyright 2026 Engenere - Felipe Motter Pereira
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
"""Link the DF-e documents to the fiscal documents they already imported.

fiscal_document_id comes with l10n_br_nfe_dfe and hides the Import button: left
empty, every document imported before this version offers to be imported again.
An end- script, because the column only exists once l10n_br_nfe_dfe is installed
in the same run. A document imported twice keeps the one not cancelled and,
among those, the most recent.
"""

from openupgradelib import openupgrade


def migrate(cr, version):
    if not openupgrade.column_exists(
        cr, "l10n_br_fiscal_dfe_document", "fiscal_document_id"
    ):
        return
    openupgrade.logged_query(
        cr,
        """
        UPDATE l10n_br_fiscal_dfe_document dfe_document
           SET fiscal_document_id = match.fiscal_document_id
          FROM (
                SELECT DISTINCT ON (candidate.id)
                       candidate.id AS dfe_document_id,
                       fiscal_document.id AS fiscal_document_id
                  FROM l10n_br_fiscal_dfe_document candidate
                  JOIN l10n_br_fiscal_document fiscal_document
                    ON fiscal_document.document_key = candidate.access_key
                   AND fiscal_document.company_id = candidate.company_id
                   AND fiscal_document.issuer = 'partner'
                 WHERE candidate.fiscal_document_id IS NULL
                 ORDER BY candidate.id,
                          fiscal_document.state_edoc = 'cancelada',
                          fiscal_document.id DESC
               ) match
         WHERE dfe_document.id = match.dfe_document_id
        """,
    )
