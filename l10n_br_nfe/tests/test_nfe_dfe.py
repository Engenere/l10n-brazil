# Copyright (C) 2023 - TODAY Felipe Zago - KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=line-too-long

from unittest import mock

from nfelib.nfe.ws.edoc_legacy import DocumentoElectronicoAdapter

from odoo.tests.common import TransactionCase

from odoo.addons.l10n_br_fiscal_dfe.tests.test_dfe import (
    mocked_post_error_status_code,
    mocked_post_success_multiple,
    mocked_post_success_single,
)

from ..models.mde import MDe


class TestNFeDFe(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.dfe_monitor = cls.env["l10n_br_fiscal.dfe_monitor"].create(
            {"company_id": cls.env.ref("l10n_br_base.empresa_lucro_presumido").id}
        )

    @mock.patch.object(
        DocumentoElectronicoAdapter,
        "_post",
        side_effect=mocked_post_success_single,
    )
    @mock.patch.object(MDe, "action_ciencia_emissao", return_value=None)
    def test_download_document_proc_nfe(self, _mock_post, _mock_ciencia):
        self.dfe_monitor.search_documents()

        self.dfe_monitor.import_documents()
        self.assertEqual(len(self.dfe_monitor.imported_document_ids), 1)
        self.assertEqual(
            self.dfe_monitor.imported_document_ids[0].document_key,
            "35200159594315000157550010000000012062777161",
        )

    @mock.patch.object(
        DocumentoElectronicoAdapter, "_post", side_effect=mocked_post_success_multiple
    )
    def test_search_dfe_success(self, _mock_post):
        self.dfe_monitor.search_documents()
        self.assertEqual(self.dfe_monitor.dfe_ids[-1].nsu, self.dfe_monitor.last_nsu)

        dfe1, dfe2 = self.dfe_monitor.dfe_ids
        self.assertEqual(dfe1.company_id, self.dfe_monitor.company_id)
        self.assertEqual(dfe1.key, "31201010588201000105550010038421171838422178")
        self.assertEqual(dfe1.emitter, "ZAP GRAFICA E EDITORA EIRELI")
        self.assertEqual(dfe1.cnpj_cpf, "10.588.201/0001-05")

        attachment_1 = self.env["ir.attachment"].search([("res_id", "=", dfe1.id)])
        self.assertTrue(attachment_1)

        self.assertEqual(dfe2.company_id, self.dfe_monitor.company_id)
        self.assertEqual(dfe2.key, "35200159594315000157550010000000012062777161")
        self.assertEqual(
            dfe2.partner_id, self.env.ref("l10n_br_base.simples_nacional_partner")
        )
        self.assertEqual(dfe2.cnpj_cpf, "59.594.315/0001-57")

        attachment_2 = self.env["ir.attachment"].search([("res_id", "=", dfe2.id)])
        self.assertTrue(attachment_2)

    @mock.patch.object(
        DocumentoElectronicoAdapter,
        "_post",
        side_effect=mocked_post_success_single,
    )
    @mock.patch.object(MDe, "action_ciencia_emissao", return_value=None)
    def test_import_documents(self, _mock_post, _mock_ciencia):
        self.dfe_monitor.search_documents()
        self.dfe_monitor.import_documents()

        document_id = self.dfe_monitor.dfe_ids[0].document_id
        self.assertTrue(document_id)
        self.assertEqual(document_id.dfe_monitor, self.dfe_monitor)

        with mock.patch.object(
            DocumentoElectronicoAdapter,
            "_post",
            side_effect=mocked_post_error_status_code,
        ):
            xml = self.dfe_monitor._download_document("dummy")
            self.assertIsNone(xml)

    # def test_create_dfe(self):
    #     # dfe = self.dfe_id._create_dfe_from_resNFe("dummy_v1.0")
    #     # self.assertIsNone(dfe)

    #     dfe_id = self.env["l10n_br_fiscal.dfe"].create({"key": "123456789"})

    #     mock_resNFe = mock.MagicMock(spec=["chNFe"])
    #     mock_resNFe.chNFe = "123456789"
    #     resnfe_dfe_id = self.dfe_id._create_dfe_from_resNFe(mock_resNFe)
    #     self.assertEqual(resnfe_dfe_id, dfe_id)

    #     mock_procNFe = mock.MagicMock(spec=["protNFe"])
    #     mock_procNFe.protNFe.infProt.chNFe = "123456789"
    #     procnfe_dfe_id = self.dfe_id._create_dfe_from_procNFe(mock_procNFe)
    #     self.assertEqual(procnfe_dfe_id, dfe_id)
