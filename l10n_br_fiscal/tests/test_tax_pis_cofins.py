# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class TestTaxPisCofinsNcm(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env["l10n_br_fiscal.tax.pis.cofins"]
        # NCMs available in demo mode (see demo/__init__.py DEMO_NCM)
        cls.ncm_a = cls.env.ref("l10n_br_fiscal.ncm_22030000")
        cls.ncm_b = cls.env.ref("l10n_br_fiscal.ncm_73239900")
        cls.ncm_c = cls.env.ref("l10n_br_fiscal.ncm_73269090")

    def _create(self, **vals):
        vals.setdefault("code", "TEST_PISCOFINS")
        vals.setdefault("name", "Test PIS/COFINS setup")
        return self.model.create(vals)

    def test_not_in_ncms_without_ncms_matches_nothing(self):
        record = self._create(not_in_ncms="73269090")
        self.assertFalse(record.ncm_ids)

    def test_ncm_exception_without_ncms_matches_nothing(self):
        record = self._create(ncm_exception="01")
        self.assertFalse(record.ncm_ids)

    def test_ncms_without_exclusions(self):
        record = self._create(ncms="22030000,73269090")
        self.assertEqual(record.ncm_ids, self.ncm_a | self.ncm_c)

    def test_not_in_ncms_excludes_listed_ncms(self):
        record = self._create(ncms="22030000,73239900", not_in_ncms="73239900")
        self.assertEqual(record.ncm_ids, self.ncm_a)

    def test_write_not_in_ncms_recomputes(self):
        record = self._create(ncms="22030000,73269090")
        self.assertEqual(record.ncm_ids, self.ncm_a | self.ncm_c)
        record.not_in_ncms = "73269090"
        self.assertEqual(record.ncm_ids, self.ncm_a)

    def test_agricultural_pesticides_zero_rate_is_not_applied_by_ncm(self):
        """The zero rate for agricultural pesticides (Lei 10.925/2004, art.
        1, II) depends on the product being registered at MAPA, which the
        NCM does not tell: heading 38.08 also holds household disinfectants
        such as sodium hypochlorite bleach (3808.94.19 Ex 02), registered at
        the health ministry. Mapped by NCM, this setup zeroed PIS/COFINS on
        their sales once it became the only setup of the whole heading."""
        setup = self.env.ref("l10n_br_fiscal.tax_piscofins_4313_102")
        ncm_model = self.env["l10n_br_fiscal.ncm"].with_context(active_test=False)
        bleach = ncm_model.search(
            [("code", "=", "3808.94.19"), ("exception", "=", "02")]
        ) or ncm_model.create(
            {
                "code": "3808.94.19",
                "exception": "02",
                "name": "Ex 02 - À base de hipoclorito de sódio",
            }
        )
        bleach.active = True
        setup._compute_ncms()
        result = self.env.ref("l10n_br_fiscal.fo_venda_venda").map_fiscal_taxes(
            company=self.env.ref("l10n_br_base.empresa_lucro_presumido"),
            partner=self.env.ref("l10n_br_base.res_partner_cliente1_sp"),
            product=self.env.ref("product.product_product_6"),
            ncm=bleach,
            nbm=self.env["l10n_br_fiscal.nbm"],
            nbs=self.env["l10n_br_fiscal.nbs"],
            cest=self.env["l10n_br_fiscal.cest"],
            city_taxation_code=self.env["l10n_br_fiscal.city.taxation.code"],
            national_taxation_code=self.env["l10n_br_fiscal.national.taxation.code"],
            service_type=self.env["l10n_br_fiscal.service.type"],
            ind_final="1",
        )
        self.assertNotEqual(
            result["taxes"].get(setup.tax_pis_id.tax_domain), setup.tax_pis_id
        )
        self.assertNotEqual(
            result["taxes"].get(setup.tax_cofins_id.tax_domain), setup.tax_cofins_id
        )
        self.assertNotIn(setup, bleach.piscofins_ids)

    def test_write_ncm_exception_recomputes(self):
        record = self._create(ncms="73269090")
        self.assertEqual(record.ncm_ids, self.ncm_c)
        # no NCM with exception "99" exists, so nothing matches
        record.ncm_exception = "99"
        self.assertFalse(record.ncm_ids)
