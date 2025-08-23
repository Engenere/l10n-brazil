# Copyright (C) 2023-Today - Engenere (<https://engenere.one>).
# @author Felipe Motter Pereira <felipe@engenere.one>

from datetime import datetime, time, timedelta

from pytz import UTC, timezone

from odoo import Command
from odoo.tests import TransactionCase

from odoo.addons.l10n_br_fiscal.constants.fiscal import DOCUMENT_ISSUER_PARTNER


class TestDocumentDate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.fiscal_operation_id = cls.env.ref("l10n_br_fiscal.fo_venda")

        product_id = cls.env.ref("product.product_product_7")

        invoice_line_vals = [
            Command.create(
                {
                    "fiscal_operation_line_id": cls.env.ref(
                        "l10n_br_fiscal.fo_venda_revenda"
                    ).id,
                    "product_id": product_id.id,
                    "quantity": 1,
                    "price_unit": 1000.0,
                }
            )
        ]

        cls.move_id = cls.env["account.move"].create(
            {
                "partner_id": cls.env.ref("base.res_partner_3").id,
                "document_type_id": cls.env.ref("l10n_br_fiscal.document_55").id,
                "document_serie_id": cls.env.ref(
                    "l10n_br_fiscal.empresa_lc_document_55_serie_1"
                ).id,
                "fiscal_operation_id": cls.fiscal_operation_id.id,
                "move_type": "out_invoice",
                "invoice_line_ids": invoice_line_vals,
            }
        )

    def test_document_date(self):
        self.move_id.issuer = DOCUMENT_ISSUER_PARTNER
        user_tz = timezone(self.env.user.tz or "UTC")
        original_date = datetime.combine(datetime.now().date(), time.min)
        # Convert the original_date to the user's timezone and remove the time for
        # comparison
        original_date_in_user_tz = (
            user_tz.localize(original_date).astimezone(UTC).replace(tzinfo=None)
        )
        original_date_without_time = original_date_in_user_tz.date()

        self.move_id.invoice_date = original_date.date()

        self.assertEqual(
            self.move_id.fiscal_document_id.document_date.date(),
            original_date_without_time,
            "Computed document date is incorrect",
        )

    def test_inverse_document_date(self):
        self.move_id.issuer = DOCUMENT_ISSUER_PARTNER
        new_date = datetime.now() - timedelta(days=2)
        self.move_id.fiscal_document_id.document_date = new_date

        self.assertEqual(
            self.move_id.invoice_date,
            new_date.date(),
            "Inverse computed invoice date is incorrect",
        )

    def test_date_in_out(self):
        self.move_id.issuer = DOCUMENT_ISSUER_PARTNER
        user_tz = timezone(self.env.user.tz or "UTC")
        original_date = datetime.combine(datetime.now().date(), time.min)
        # Convert the original_date to the user's timezone and remove the time for
        # comparison
        original_date_in_user_tz = (
            user_tz.localize(original_date).astimezone(UTC).replace(tzinfo=None)
        )
        original_date_without_time = original_date_in_user_tz.date()
        self.move_id.date = original_date.date()

        self.assertEqual(
            self.move_id.fiscal_document_id.date_in_out.date(),
            original_date_without_time,
            "Computed date in out is incorrect",
        )

    def test_inverse_date_in_out(self):
        self.move_id.issuer = DOCUMENT_ISSUER_PARTNER
        new_date = datetime.now() - timedelta(days=2)
        self.move_id.fiscal_document_id.date_in_out = new_date
        self.assertEqual(
            self.move_id.date,
            new_date.date(),
            "Inverse computed account date is incorrect",
        )
