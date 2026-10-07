# Copyright 2026 Engenere (<https://engenere.one>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from psycopg2 import sql

from odoo import models

_logger = logging.getLogger(__name__)


class DataNaturalKeyMixin(models.AbstractModel):
    """
    Adopt existing records by natural key when loading data files.

    When a data file (CSV or XML) brings a record whose xml_id is not in the
    database yet, but a record with the same natural key already exists
    (created by hand, imported, or a legacy record that lost its xml_id),
    the xml_id is bound to that record instead of creating a duplicate.
    Odoo then handles it as a regular existing record, so the usual
    noupdate rules decide whether the file values are written or not.
    """

    _name = "l10n_br_fiscal.data.natural.key.mixin"
    _description = "Fiscal Data Natural Key Mixin"

    # Fields identifying a record regardless of its xml_id. Empty disables it.
    _natural_key = ()

    def _natural_key_value(self, field_name, value):
        """Normalize one natural key component (hook for masks, case, etc.)."""
        return value or False

    def _natural_key_from_values(self, values):
        return tuple(
            self._natural_key_value(field_name, values.get(field_name))
            for field_name in self._natural_key
        )

    def _natural_key_from_record(self):
        self.ensure_one()
        return tuple(
            self._natural_key_value(field_name, self[field_name])
            for field_name in self._natural_key
        )

    def _load_records(self, data_list, update=False):
        if self._natural_key:
            self._adopt_records_by_natural_key(data_list)
        return super()._load_records(data_list, update=update)

    def _adopt_records_by_natural_key(self, data_list):
        imd = self.env["ir.model.data"].sudo()
        xml_ids = [data["xml_id"] for data in data_list if data.get("xml_id")]
        # xml_ids pointing to a deleted record are adoptable as well
        known = {
            f"{row[1]}.{row[2]}" for row in imd._lookup_xmlids(xml_ids, self) if row[6]
        }
        unknown = [
            data
            for data in data_list
            if data.get("xml_id") and data["xml_id"] not in known
        ]
        if not unknown:
            return

        # Candidates: records without an xml_id from the loading module(s).
        # On a fresh install the table is empty and this returns nothing.
        modules = tuple({data["xml_id"].split(".", 1)[0] for data in unknown})
        self.env.cr.execute(
            sql.SQL(
                """
                SELECT rec.id
                  FROM {table} rec
                 WHERE NOT EXISTS (
                    SELECT 1
                      FROM ir_model_data imd
                     WHERE imd.model = %s
                       AND imd.res_id = rec.id
                       AND imd.module IN %s
                 )
                 ORDER BY rec.id
                """
            ).format(table=sql.Identifier(self._table)),
            (self._name, modules),
        )
        candidate_ids = [row[0] for row in self.env.cr.fetchall()]
        if not candidate_ids:
            return

        candidates_by_key = {}
        for record in self.with_context(active_test=False).browse(candidate_ids):
            candidates_by_key.setdefault(record._natural_key_from_record(), []).append(
                record
            )

        to_bind = []
        for data in unknown:
            key = self._natural_key_from_values(data["values"])
            matches = candidates_by_key.get(key)
            if not matches:
                continue
            record = matches.pop(0)
            if matches:
                _logger.warning(
                    "%s: %d other records share the natural key %s with %s, "
                    "only the oldest one was adopted as %s",
                    self._name,
                    len(matches),
                    key,
                    record,
                    data["xml_id"],
                )
            _logger.info(
                "%s: adopting %s as %s (natural key %s)",
                self._name,
                record,
                data["xml_id"],
                key,
            )
            to_bind.append(
                {
                    "xml_id": data["xml_id"],
                    "record": record,
                    "noupdate": data.get("noupdate", False),
                }
            )
        if to_bind:
            # update=False: also re-point xml_ids left dangling by a deleted record
            imd._update_xmlids(to_bind, update=False)
