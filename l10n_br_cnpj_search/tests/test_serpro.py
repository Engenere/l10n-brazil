# Copyright 2022 KMEE
# Copyright (C) 2024-Today - Engenere (<https://engenere.one>).
# @author Cristiano Mafra Junior
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from unittest import mock

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import TestCnpjCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestTestSerPro(TestCnpjCommon):
    def setUp(self):
        super().setUp()

        self.set_param("cnpj_provider", "serpro")
        self.set_param("serpro_token", "06aef429-a981-3ec5-a1f8-71d38d86481e")
        self.set_param("serpro_trial", True)
        self.set_param("serpro_schema", "basica")

    def test_serpro_basica(self):
        dummy_basica = self.model.create(
            {"name": "Dummy Basica", "cnpj_cpf": "34.238.864/0001-68"}
        )
        dummy_basica._onchange_cnpj_cpf()

        action_wizard = dummy_basica.action_open_cnpj_search_wizard()
        wizard_context = action_wizard.get("context")
        wizard = (
            self.env["partner.search.wizard"].with_context(**wizard_context).create({})
        )
        wizard.action_update_partner()
        self.assertEqual(
            dummy_basica.legal_name,
            "Uhieqkx Whnhiwd Nh Fixkhuuwphmvx Nh Nwnxu (Uhifix)",
        )
        self.assertEqual(dummy_basica.company_type, "company")
        self.assertEqual(dummy_basica.name, "Uhifix Uhnh")
        self.assertEqual(dummy_basica.email, "EMPRESA@XXXXXX.BR")
        self.assertEqual(dummy_basica.street_name, "Nh Biwmnh Wihw Mxivh")
        self.assertEqual(dummy_basica.street2, "Lote V")
        self.assertEqual(dummy_basica.street_number, "Q.601")
        self.assertEqual(dummy_basica.zip, "70836900")
        self.assertEqual(dummy_basica.district, "Asa Norte")
        self.assertEqual(dummy_basica.phone, "(61) 22222222")
        self.assertEqual(dummy_basica.mobile, "(61) 22222222")
        self.assertEqual(dummy_basica.state_id.code, "DF")
        self.assertEqual(dummy_basica.equity_capital, 0)
        self.assertEqual(dummy_basica.cnae_main_id.code, "6204-0/00")

    def test_serpro_not_found(self):
        # In the Trial version there are only a few registered CNPJ records
        invalid = self.model.create(
            {"name": "invalid", "cnpj_cpf": "44.356.113/0001-08"}
        )
        invalid._onchange_cnpj_cpf()

        with self.assertRaises(ValidationError):
            action_wizard = invalid.action_open_cnpj_search_wizard()
            wizard_context = action_wizard.get("context")
            self.env["partner.search.wizard"].with_context(**wizard_context).create({})

    def assert_socios(self, partner, expected_cnpjs):
        socios = self.model.search_read(
            [("id", "in", partner.child_ids.ids)],
            fields=["name", "cnpj_cpf", "company_type"],
        )

        for s in socios:
            s.pop("id")

        expected_socios = [
            {
                "name": "Joana Alves Mundim Pena",
                "cnpj_cpf": expected_cnpjs["Joana"],
                "company_type": "person",
            },
            {
                "name": "Luiza Aldenora",
                "cnpj_cpf": expected_cnpjs["Aldenora"],
                "company_type": "person",
            },
            {
                "name": "Luiza Araujo De Oliveira",
                "cnpj_cpf": expected_cnpjs["Araujo"],
                "company_type": "person",
            },
            {
                "name": "Luiza Barbosa Bezerra",
                "cnpj_cpf": expected_cnpjs["Barbosa"],
                "company_type": "person",
            },
            {
                "name": "Marcelo Antonio Barros De Cicco",
                "cnpj_cpf": expected_cnpjs["Marcelo"],
                "company_type": "person",
            },
        ]

        self.assertEqual(socios, expected_socios)

    def test_serpro_empresa(self):
        mocked_response = {
            "ni": "34238864000168",
            "nomeEmpresarial": "UHIEQKX WHNHIWD NH  FIXKHUUWPHMVX NH NWNXU (UHIFIX)",
            "nomeFantasia": "UHIFIX UHNH",
            "telefones": [
                {"ddd": "61", "numero": "22222222"},
                {"ddd": "61", "numero": "22222222"},
            ],
            "cep": "70836900",
            "correioEletronico": "EMPRESA@XXXXXX.BR",
            "socios": [
                {
                    "tipoSocio": "2",
                    "cpf": "07119488449",
                    "nome": "LUIZA ARAUJO DE OLIVEIRA",
                    "qualificacao": "49",
                    "dataInclusao": "2014-01-01",
                    "pais": {"codigo": "105", "descricao": "BRASIL"},
                    "representanteLegal": {
                        "cpf": "00000000000",
                        "nome": "",
                        "qualificacao": "00",
                    },
                },
                {
                    "tipoSocio": "2",
                    "cpf": "23982012600",
                    "nome": "JOANA ALVES MUNDIM PENA",
                    "qualificacao": "49",
                    "dataInclusao": "2014-01-01",
                    "pais": {"codigo": "105", "descricao": "BRASIL"},
                    "representanteLegal": {
                        "cpf": "00000000000",
                        "nome": "",
                        "qualificacao": "00",
                    },
                },
                {
                    "tipoSocio": "2",
                    "cpf": "13946994415",
                    "nome": "LUIZA BARBOSA BEZERRA",
                    "qualificacao": "49",
                    "dataInclusao": "2014-01-01",
                    "pais": {"codigo": "105", "descricao": "BRASIL"},
                    "representanteLegal": {
                        "cpf": "00000000000",
                        "nome": "",
                        "qualificacao": "00",
                    },
                },
                {
                    "tipoSocio": "2",
                    "cpf": "00031298702",
                    "nome": "MARCELO ANTONIO BARROS DE CICCO",
                    "qualificacao": "49",
                    "dataInclusao": "2014-01-01",
                    "pais": {"codigo": "105", "descricao": "BRASIL"},
                    "representanteLegal": {
                        "cpf": "00000000000",
                        "nome": "",
                        "qualificacao": "00",
                    },
                },
                {
                    "tipoSocio": "2",
                    "cpf": "76822320300",
                    "nome": "LUIZA ALDENORA",
                    "qualificacao": "49",
                    "dataInclusao": "2014-01-01",
                    "pais": {"codigo": "105", "descricao": "BRASIL"},
                    "representanteLegal": {
                        "cpf": "00000000000",
                        "nome": "",
                        "qualificacao": "00",
                    },
                },
            ],
            "endereco": {
                "tipoLogradouro": "SETOR",
                "logradouro": "NH BIWMNH WIHW MXIVH",
                "numero": "Q.601",
                "complemento": "LOTE V",
                "cep": "70836900",
                "bairro": "ASA NORTE",
                "municipio": {"codigo": "9701", "descricao": "BRASILIA"},
                "uf": "DF",
                "pais": {"codigo": "105", "descricao": "BRASIL"},
            },
            "naturezaJuridica": {"codigo": "2011", "descricao": "Empresa Pública"},
            "capitalSocial": 0,
            "cnaePrincipal": {
                "codigo": "6204000",
                "descricao": "Consultoria em tecnologia da informação",
            },
        }
        with mock.patch(
            "odoo.addons.l10n_br_cnpj_search.models.cnpj_webservice.CNPJWebservice.validate",
            return_value=mocked_response,
        ):
            self.model.search([("cnpj_cpf", "=", "34.238.864/0001-68")]).write(
                {"active": False}
            )
            self.set_param("serpro_schema", "empresa")

            dummy_empresa = self.model.create(
                {"name": "Dummy Empresa", "cnpj_cpf": "34.238.864/0001-68"}
            )

            dummy_empresa._onchange_cnpj_cpf()
            action_wizard = dummy_empresa.action_open_cnpj_search_wizard()
            wizard_context = action_wizard.get("context")
            wizard = (
                self.env["partner.search.wizard"]
                .with_context(**wizard_context)
                .create({})
            )
            wizard.action_update_partner()

        expected_cnpjs = {
            "Joana": "23982012600",
            "Aldenora": "76822320300",
            "Araujo": "07119488449",
            "Barbosa": "13946994415",
            "Marcelo": "00031298702",
        }

        self.assert_socios(dummy_empresa, expected_cnpjs)

    def test_serpro_qsa(self):
        mocked_response = {
            "nomeEmpresarial": "UHIEQKX WHNHIWD NH  FIXKHUUWPHMVX NH NWNXU (UHIFIX)",
            "nomeFantasia": "UHIFIX UHNH",
            "telefones": [
                {"ddd": "61", "numero": "22222222"},
                {"ddd": "61", "numero": "22222222"},
            ],
            "cep": "70836900",
            "correioEletronico": "EMPRESA@XXXXXX.BR",
            "socios": [
                {
                    "tipoSocio": "2",
                    "nome": "LUIZA ARAUJO DE OLIVEIRA",
                    "qualificacao": "49",
                    "pais": {"codigo": "105", "descricao": "BRASIL"},
                    "representanteLegal": {"nome": "", "qualificacao": "00"},
                },
                {
                    "tipoSocio": "2",
                    "nome": "JOANA ALVES MUNDIM PENA",
                    "qualificacao": "49",
                    "pais": {"codigo": "105", "descricao": "BRASIL"},
                    "representanteLegal": {"nome": "", "qualificacao": "00"},
                },
                {
                    "tipoSocio": "2",
                    "nome": "LUIZA BARBOSA BEZERRA",
                    "qualificacao": "49",
                    "pais": {"codigo": "105", "descricao": "BRASIL"},
                    "representanteLegal": {"nome": "", "qualificacao": "00"},
                },
                {
                    "tipoSocio": "2",
                    "nome": "MARCELO ANTONIO BARROS DE CICCO",
                    "qualificacao": "49 ",
                    "pais": {"codigo": "105", "descricao": "BRASIL"},
                    "representanteLegal": {"nome": "", "qualificacao": "00"},
                },
                {
                    "tipoSocio": "2",
                    "nome": "LUIZA ALDENORA",
                    "qualificacao": "49",
                    "pais": {"codigo": "105", "descricao": "BRASIL"},
                    "representanteLegal": {"nome": "", "qualificacao": "00"},
                },
            ],
            "endereco": {
                "tipoLogradouro": "SETOR",
                "logradouro": "NH BIWMNH WIHW MXIVH",
                "numero": "Q.601",
                "complemento": "LOTE V",
                "cep": "70836900",
                "bairro": "ASA NORTE",
                "municipio": {"codigo": "9701", "descricao": "BRASILIA"},
                "uf": "DF",
                "pais": {"codigo": "105", "descricao": "BRASIL"},
            },
            "naturezaJuridica": {"codigo": "2011", "descricao": "Empresa Pública"},
            "capitalSocial": 0,
            "cnaePrincipal": {
                "codigo": "6204000",
                "descricao": "Consultoria em tecnologia da informação",
            },
        }
        with mock.patch(
            "odoo.addons.l10n_br_cnpj_search.models.cnpj_webservice.CNPJWebservice.validate",
            return_value=mocked_response,
        ):
            self.model.search([("cnpj_cpf", "=", "34.238.864/0001-68")]).write(
                {"active": False}
            )
            self.set_param("serpro_schema", "qsa")

            dummy_qsa = self.model.create(
                {"name": "Dummy QSA", "cnpj_cpf": "34.238.864/0001-68"}
            )

            dummy_qsa._onchange_cnpj_cpf()
            action_wizard = dummy_qsa.action_open_cnpj_search_wizard()
            wizard_context = action_wizard.get("context")
            wizard = (
                self.env["partner.search.wizard"]
                .with_context(**wizard_context)
                .create({})
            )
            wizard.action_update_partner()

            expected_cnpjs = {
                "Joana": False,
                "Aldenora": False,
                "Araujo": False,
                "Barbosa": False,
                "Marcelo": False,
            }

            self.assert_socios(dummy_qsa, expected_cnpjs)
