# Copyright 2026 Engenere (<https://engenere.one>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase

MIXIN_LOGGER = "odoo.addons.l10n_br_fiscal.models.data_natural_key_mixin"


class TestDataNaturalKey(TransactionCase):
    """Data files adopt existing NCMs by natural key instead of duplicating."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ncm_model = cls.env["l10n_br_fiscal.ncm"]
        cls.imd_model = cls.env["ir.model.data"]
        # NCM missing from the data files, created by hand
        cls.manual_ncm = cls.ncm_model.create(
            {"code": "9999.99.01", "name": "Created by hand"}
        )
        # Same, typed without the mask
        cls.unmasked_ncm = cls.ncm_model.create(
            {"code": "99999902", "name": "Created by hand without mask"}
        )
        # Records sharing the code, told apart by the exception
        cls.ncm_without_exception = cls.ncm_model.create(
            {"code": "9999.99.03", "name": "Without exception"}
        )
        cls.ncm_with_exception = cls.ncm_model.create(
            {"code": "9999.99.03", "exception": "01", "name": "With exception"}
        )
        # NCM imported from a spreadsheet, owning an __import__ xml_id
        cls.imported_ncm = cls.ncm_model.create(
            {"code": "9999.99.04", "name": "Imported"}
        )
        cls.imd_model.create(
            {
                "module": "__import__",
                "name": "ncm_99999904",
                "model": "l10n_br_fiscal.ncm",
                "res_id": cls.imported_ncm.id,
            }
        )

    def _load_ncm(self, name, values, update=True, noupdate=True):
        """Load one NCM row the way CSV/XML data files do."""
        values = dict(values, name=values.get("name", "From data file"))
        return self.ncm_model._load_records(
            [
                {
                    "xml_id": f"l10n_br_fiscal.{name}",
                    "values": values,
                    "noupdate": noupdate,
                }
            ],
            update=update,
        )

    def _xmlid_noupdate(self, name):
        return self.imd_model.search(
            [("module", "=", "l10n_br_fiscal"), ("name", "=", name)]
        ).noupdate

    def _ncm_count(self, code, exception=False):
        return self.ncm_model.with_context(active_test=False).search_count(
            [("code", "=", code), ("exception", "=", exception)]
        )

    def test_adopt_manual_record(self):
        record = self._load_ncm("ncm_99999901", {"code": "9999.99.01"})
        self.assertEqual(record, self.manual_ncm)
        self.assertEqual(self.env.ref("l10n_br_fiscal.ncm_99999901"), self.manual_ncm)
        self.assertEqual(self._ncm_count("9999.99.01"), 1)
        # noupdate: the user values are kept on module update
        self.assertEqual(self.manual_ncm.name, "Created by hand")

    def test_adopt_record_with_unmasked_code(self):
        record = self._load_ncm("ncm_99999902", {"code": "9999.99.02"})
        self.assertEqual(record, self.unmasked_ncm)
        self.assertEqual(self._ncm_count("9999.99.02"), 0)

    def test_adopt_record_by_exception(self):
        record = self._load_ncm(
            "ncm_99999903_01", {"code": "9999.99.03", "exception": "01"}
        )
        self.assertEqual(record, self.ncm_with_exception)
        record = self._load_ncm("ncm_99999903", {"code": "9999.99.03"})
        self.assertEqual(record, self.ncm_without_exception)

    def test_adopt_record_with_foreign_xmlid(self):
        record = self._load_ncm("ncm_99999904", {"code": "9999.99.04"})
        self.assertEqual(record, self.imported_ncm)
        self.assertEqual(
            self.imd_model.search_count(
                [
                    ("model", "=", "l10n_br_fiscal.ncm"),
                    ("res_id", "=", self.imported_ncm.id),
                ]
            ),
            2,
        )

    def test_adopt_legacy_record_without_xmlid(self):
        record = self._load_ncm("ncm_99999905", {"code": "9999.99.05"})
        self.imd_model.search(
            [("module", "=", "l10n_br_fiscal"), ("name", "=", "ncm_99999905")]
        ).unlink()
        self.assertEqual(self._load_ncm("ncm_99999905", {"code": "9999.99.05"}), record)
        self.assertEqual(self._ncm_count("9999.99.05"), 1)

    def test_repoint_dangling_xmlid(self):
        self.imd_model.create(
            {
                "module": "l10n_br_fiscal",
                "name": "ncm_99999901",
                "model": "l10n_br_fiscal.ncm",
                "res_id": self.ncm_model.search([], order="id desc", limit=1).id + 1,
                "noupdate": False,
            }
        )
        record = self._load_ncm("ncm_99999901", {"code": "9999.99.01"})
        self.assertEqual(record, self.manual_ncm)
        self.assertEqual(self.env.ref("l10n_br_fiscal.ncm_99999901"), self.manual_ncm)
        self.assertTrue(self._xmlid_noupdate("ncm_99999901"))

    def test_install_keeps_record_values(self):
        record = self._load_ncm("ncm_99999901", {"code": "9999.99.01"}, update=False)
        self.assertEqual(record, self.manual_ncm)
        self.assertEqual(self.manual_ncm.name, "Created by hand")

    def test_adopted_record_is_noupdate_in_updatable_data(self):
        record = self._load_ncm("ncm_99999901", {"code": "9999.99.01"}, noupdate=False)
        self.assertEqual(record, self.manual_ncm)
        self.assertTrue(self._xmlid_noupdate("ncm_99999901"))
        self.assertEqual(self.manual_ncm.name, "Created by hand")

    def test_warn_values_kept_from_data_file(self):
        with self.assertLogs(MIXIN_LOGGER, level="WARNING") as logs:
            self._load_ncm("ncm_99999901", {"code": "9999.99.01"})
        self.assertIn("keeps its own values for name", logs.output[0])

    def test_no_warning_when_values_match(self):
        self.ncm_model.create({"code": "9999.99.07", "name": "From data file"})
        with self.assertNoLogs(MIXIN_LOGGER, level="WARNING"):
            self._load_ncm("ncm_99999907", {"code": "9999.99.07"})

    def test_ambiguous_key_adopts_oldest_record(self):
        newer_ncm = self.ncm_model.create(
            {"code": "9999.99.01", "name": "Duplicated by hand"}
        )
        with self.assertLogs(MIXIN_LOGGER, level="WARNING"):
            record = self._load_ncm("ncm_99999901", {"code": "9999.99.01"})
        self.assertEqual(record, self.manual_ncm)
        self.assertFalse(newer_ncm.get_external_id()[newer_ncm.id])

    def test_create_record_without_candidate(self):
        record = self._load_ncm("ncm_99999906", {"code": "9999.99.06"})
        self.assertEqual(record.name, "From data file")
        self.assertEqual(self._ncm_count("9999.99.06"), 1)
