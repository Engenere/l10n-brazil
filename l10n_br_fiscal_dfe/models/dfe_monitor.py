# Copyright (C) 2023 KMEE Informatica LTDA
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl)

import re

from erpbrasil.transmissao import TransmissaoSOAP
from nfelib.nfe.ws.edoc_legacy import NFeAdapter as edoc_nfe
from requests import Session

from odoo import _, api, fields, models

from ..tools import utils


class DFeMonitor(models.Model):
    _name = "l10n_br_fiscal.dfe_monitor"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Consult DF-e"
    _order = "id desc"
    _rec_name = "display_name"

    display_name = fields.Char(compute="_compute_display_name")

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company.id,
        readonly=True,
    )

    version = fields.Selection(related="company_id.dfe_version")

    environment = fields.Selection(related="company_id.dfe_environment")

    last_nsu = fields.Char(related="company_id.last_nsu", readonly=False)

    last_query = fields.Datetime(string="Last query")

    imported_document_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.document",
        inverse_name="dfe_id",
        string="Imported Documents",
    )

    use_cron = fields.Boolean(
        default=False,
        string="Download new documents automatically",
        help="If activated, allows new manifestations to be automatically "
        "searched with a Cron",
    )

    automatically_acknowledge_receipt = fields.Boolean(
        default=False,
        string="Manifestar Ciência Automaticamente",
        help="Automatically acknowledge receipt"
        "of notifications or events without manual intervention",
    )  # TODO: Vê um nome melhor pro campo

    @api.depends("company_id.name", "last_nsu")
    def name_get(self):
        return self.mapped(lambda d: (d.id, f"{d.company_id.name} - NSU: {d.last_nsu}"))

    @api.model
    def _get_processor(self):
        certificado = self.env.company._get_br_ecertificate()
        session = Session()
        session.verify = False
        return edoc_nfe(
            TransmissaoSOAP(certificado, session),
            self.company_id.state_id.ibge_code,
            versao=self.version,
            ambiente=self.environment,
        )

    @api.model
    def validate_distribution_response(self, result):
        valid = False
        message = result.resposta.xMotivo
        if result.retorno.status_code != 200:
            code = result.retorno.status_code
        elif result.resposta.cStat != "138":
            code = result.resposta.cStat
        else:
            valid = True

        if not valid:
            self.message_post(
                body=_(
                    f"Error validating document distribution: \n\n"
                    f"{code} - {message}"
                )
            )

        return valid

    @api.model
    def _document_distribution(self):
        last_nsu = (
            self.last_nsu
            if self.last_nsu and self.last_nsu.isdigit()
            else "000000000000000"
        )
        maxNSU = ""
        last_query = fields.Datetime.now()

        while maxNSU != last_nsu:
            try:
                result = self._get_processor().consultar_distribuicao(
                    cnpj_cpf=re.sub("[^0-9]", "", self.company_id.cnpj_cpf),
                    ultimo_nsu=utils.format_nsu(last_nsu),
                )
            except Exception as e:
                self.message_post(
                    body=_("Error on searching documents.\n%(error)s", error=e)
                )
                break

            last_nsu = result.resposta.ultNSU
            last_query = fields.Datetime.now()

            if not self.validate_distribution_response(result):
                break

            self._process_distribution(result)

            maxNSU = result.resposta.maxNSU
        self.write(
            {
                "last_nsu": last_nsu,
                "last_query": last_query,
            }
        )

    @api.model
    def _process_distribution(self, result):
        """Method to process the distribution data."""

    @api.model
    def _parse_xml_document(self, document):
        schema_type = document.schema.split("_")[0]
        method = "parse_%s" % schema_type
        if not hasattr(self, method):
            return

        xml = utils.parse_gzip_xml(document.valueOf_)
        return getattr(self, method)(xml)

    @api.model
    def _download_document(self, nfe_key):
        try:
            result = self._get_processor().consultar_distribuicao(
                chave=nfe_key, cnpj_cpf=re.sub("[^0-9]", "", self.company_id.cnpj_cpf)
            )
        except Exception as e:
            self.message_post(body=_("Error on searching documents.\n%s" % e))
            return

        if not self.validate_distribution_response(result):
            return

        return result.resposta.loteDistDFeInt.docZip[0]

    @api.model
    def _cron_search_documents(self):
        self.search([("use_cron", "=", True)]).search_documents()

    def search_documents(self):
        for record in self:
            record._document_distribution()

    _sql_constraints = [
        (
            "unique_company_id",
            "unique(company_id)",
            "A DF-e Monitor already exists for this company",
        ),
    ]
