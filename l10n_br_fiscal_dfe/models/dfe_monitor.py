# Copyright (C) 2023 KMEE Informatica LTDA
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl)

import base64
import gzip
import logging
import re
from datetime import datetime, timedelta
from io import BytesIO

from lxml import objectify
from nfelib.nfe.bindings.v4_0.leiaute_nfe_v4_00 import TnfeProc
from nfelib.nfe.client.v4_0.dfe import DfeClient

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..tools import utils

_logger = logging.getLogger(__name__)


class DFeMonitor(models.Model):
    _name = "l10n_br_fiscal_dfe.dfe_monitor"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "DF-e Monitor"
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

    max_nsu = fields.Char(string="Max NSU", readonly=True)

    last_query = fields.Datetime()

    last_status = fields.Char(readonly=True)

    last_status_code = fields.Char(readonly=True)

    auto_fetch = fields.Boolean(
        default=False,
        string="Auto-fetch DF-e",
        help="Periodically queries DF-e distribution for new documents",
    )

    auto_manifest_nfe = fields.Boolean(
        default=False,
        string="Automatic Recipient Manifestation (NF-e)",
        help="Automatically acknowledge receipt"
        "of notifications or events without manual intervention",
    )  # TODO: Vê um nome melhor pro campo

    dfe_document_ids = fields.One2many(
        comodel_name="l10n_br_fiscal_dfe.document",
        inverse_name="dfe_monitor_id",
        string="Chave de Acesso",
    )

    dfe_ids = fields.One2many(
        comodel_name="l10n_br_fiscal_dfe.dfe",
        inverse_name="dfe_monitor_id",
        string="Documentos Fiscais Eletrônicos",
    )

    @api.depends("company_id.name", "last_nsu")
    def name_get(self):
        return self.mapped(lambda d: (d.id, f"{d.company_id.name} - NSU: {d.last_nsu}"))

    @api.model
    def _get_processor(self):
        cert = base64.b64decode(self.company_id.certificate.file)
        return DfeClient(
            ambiente=self.environment,
            uf=self.company_id.state_id.ibge_code,
            pkcs12_data=cert,
            pkcs12_password=self.company_id.certificate.password,
            wrap_response=True,
        )

    @api.model
    def validate_distribution_response(self, result, raise_message=False):
        valid = False
        message = result.resposta.xMotivo
        if result.retorno.status_code != 200:
            code = result.retorno.status_code
        elif result.resposta.cStat != "138":
            code = result.resposta.cStat
        else:
            valid = True

        if not valid:
            msg_error = _(
                "Error validating document distribution: \n\n" f"{code} - {message}"
            )
            if raise_message:
                raise ValidationError(msg_error)
            else:
                self.message_post(body=msg_error)
        return valid

    def action_document_distribution(self):
        self.ensure_one()
        action = self._document_distribution()
        return action

    def _search_specific_document(self, access_key=None, nsu=None):
        """
        Search for a specific document by access key or NSU.
        """
        self.ensure_one()
        result = self._get_processor().consultar_distribuicao(
            chave=access_key,
            nsu_especifico=utils.format_nsu(nsu) if nsu else None,
            cnpj_cpf=re.sub("[^0-9]", "", self.company_id.vat),
        )
        if not self.validate_distribution_response(result, raise_message=True):
            return
        self._process_distribution(result)

    def _document_distribution(self):
        self.ensure_one()
        last_nsu = (
            self.last_nsu
            if (self.last_nsu and self.last_nsu.isdigit())
            else "000000000000000"
        )
        raw_max = (self.max_nsu or "").strip()
        max_nsu = raw_max if (raw_max and raw_max != "000000000000000") else False
        last_query = self.last_query or fields.Datetime.now()

        if self.last_status_code == "656":
            if fields.Datetime.now() - last_query < timedelta(hours=1):
                # Bloqueado - Consumo Indevido
                # self.message_post(body=_(
                #     "Consumo Indevido detected.\n"
                #     "Waiting 1 hour before making a new request."
                # ))
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Consumo Indevido detected"),
                        "message": _("Waiting 1 hour before making a new request."),
                        "type": "warning",
                        "sticky": False,
                    },
                }

        # TODO: rever essa lógica
        # Pode acontecer do usuário querer forçar uma nova consulta
        # if max_nsu and last_nsu >= max_nsu:
        #     if self.last_status_code == "137":
        #         # Bloqueado - Sem novos documentos
        #         if fields.Datetime.now() - last_query < timedelta(hours=1):
        #             self.message_post(
        #                 body=_(
        #                     "No new documents to download.\n"
        #                     "Waiting 1 hour before making a new request."
        #                 )
        #             )
        #             return

        last_query_success = None
        result = False
        while True:
            try:
                result = self._get_processor().consultar_distribuicao(
                    cnpj_cpf=re.sub("[^0-9]", "", self.company_id.vat),
                    ultimo_nsu=utils.format_nsu(last_nsu),
                )
            except Exception as e:
                self.message_post(
                    body=_("Error on searching documents.\n%(error)s", error=e)
                )
                break

            last_query_success = fields.Datetime.now()
            last_nsu = result.resposta.ultNSU
            max_nsu = result.resposta.maxNSU

            if not self.validate_distribution_response(result):
                break

            self._process_distribution(result)

            if last_nsu >= max_nsu:
                # Não há mais documentos para baixar
                break

        self.write(
            {
                "last_nsu": last_nsu,
                "last_query": last_query_success or self.last_query,
                "last_status": getattr(result.resposta, "xMotivo", "")
                if result
                else "",
                "last_status_code": getattr(result.resposta, "cStat", "")
                if result
                else "",
                "max_nsu": max_nsu,
            }
        )

    @api.model
    def _process_distribution(self, result):
        """Method to process the distribution data."""

    @api.model
    def _parse_xml_document(self, document):
        """
        Parse the content of a DocZip object returned by the nfelib client.
        'document' is an xsdata dataclass object.
        """

        # The xsdata binding for docZip has 'schema_value' and 'value' attributes.
        schema_type = document.schema_value.split("_")[0]
        method_name = f"parse_{schema_type}"

        try:
            # Get the parsing method (e.g., parse_procNFe from l10n_br_nfe)
            parse_method = getattr(self, method_name)
        except AttributeError:
            _logger.info(
                f"DF-e parsing method '{method_name}' not found. Skipping document."
            )
            return None

        # The 'value' attribute contains the RAW gzipped bytes, not base64.
        # We decompress it directly here.
        xml_stream = gzip.GzipFile(fileobj=BytesIO(document.value))
        return parse_method(xml_stream)

    @api.model
    def _download_document(self, nfe_key):
        try:
            result = self._get_processor().consultar_distribuicao(
                chave=nfe_key, cnpj_cpf=re.sub("[^0-9]", "", self.company_id.vat)
            )
        except Exception as e:
            self.message_post(body=_("Error on searching documents.\n%s" % e))
            return

        if not self.validate_distribution_response(result):
            return

        return result.resposta.loteDistDFeInt.docZip[0]

    @api.model
    def _cron_search_documents(self):
        self.search([("auto_fetch", "=", True)]).search_documents()

    def search_documents(self):
        for record in self:
            record._document_distribution()

    def action_search_specific(self):
        self.ensure_one()
        return {
            "name": _("Specific Document Search"),
            "type": "ir.actions.act_window",
            "res_model": "dfe_specific_search_wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_dfe_monitor_id": self.id},
        }

    def _process_distribution(self, result):
        for doc in result.resposta.loteDistDFeInt.docZip:
            payload = getattr(doc, "value", None)
            if payload is None:
                payload = getattr(doc, "valueOf_", None)
            if payload is None:
                continue
            # TODO: ve isso depois mais aqui é vier str antigo usa base64
            # se vier como bytes novo: converte para base 64
            # (parse_gzip_xml exige base64) verificar isso dps?
            if isinstance(payload, bytes):
                from base64 import b64encode

                b64_payload = b64encode(payload).decode()
            else:
                b64_payload = payload

            xml = utils.parse_gzip_xml(b64_payload).read()
            root = objectify.fromstring(xml)
            nsu_raw = getattr(doc, "NSU", None) or getattr(doc, "nsu", None)
            nsu = utils.format_nsu(nsu_raw)

            dfe_id = self.env["l10n_br_fiscal_dfe.dfe"].search(
                [("nsu", "=", nsu), ("company_id", "=", self.company_id.id)], limit=1
            )
            if dfe_id:
                continue

            schema = (
                getattr(doc, "schema_value", None) or getattr(doc, "schema", "") or ""
            )
            schema_type = schema.split("_")[0]
            if schema_type == "procNFe":
                dfe_id = self._create_dfe_from_procNFe(root, nsu)
            elif schema_type == "resNFe":
                dfe_id = self._create_dfe_from_resNFe(root, nsu)
            elif schema_type == "resEvento":
                dfe_id = self._create_dfe_from_resEvento(root, nsu)
            elif schema_type == "procEventoNFe":
                dfe_id = self._create_dfe_from_procEventoNFe(root, nsu)
            else:
                dfe_id = self.env["l10n_br_fiscal_dfe.dfe"].create(
                    {
                        "nsu": nsu,
                        "inclusion_datetime": datetime.now(),
                        "dfe_monitor_id": self.id,
                        "company_id": self.company_id.id,
                    }
                )
            if dfe_id:
                dfe_id.schema_type = schema_type
                dfe_id.create_xml_attachment(xml)

    @api.model
    def _create_dfe_from_procNFe(self, root, nsu):
        nfe_key = root.protNFe.infProt.chNFe
        access_key = self._get_or_create_document(nfe_key)
        supplier_cnpj = utils.mask_cnpj("%014d" % root.NFe.infNFe.emit.CNPJ)

        dfe = self.env["l10n_br_fiscal_dfe.dfe"].create(
            {
                "document_number": root.NFe.infNFe.ide.nNF,
                "emitter": root.NFe.infNFe.emit.xNome,
                "access_key": nfe_key,
                "serie": root.NFe.infNFe.ide.serie,
                "operation_type": str(root.NFe.infNFe.ide.tpNF),
                "document_amount": root.NFe.infNFe.total.ICMSTot.vNF,
                "inclusion_datetime": datetime.now(),
                "vat": supplier_cnpj,
                "ie": root.NFe.infNFe.emit.IE,
                "emission_datetime": datetime.strptime(
                    str(root.NFe.infNFe.ide.dhEmi)[:19],
                    "%Y-%m-%dT%H:%M:%S",
                ),
                "nsu": nsu,
                "company_id": self.company_id.id,
                "dfe_monitor_id": self.id,
                "dfe_nfe_document_type": "dfe_nfe_complete",
                "document_state": "1",  # Autorizada
            }
        )

        access_key.dfe_ids = [(4, dfe.id)]
        return dfe

    @api.model
    def _create_dfe_from_resNFe(self, root, nsu):
        nfe_key = root.chNFe
        dfe_document_id = self._get_or_create_document(nfe_key)
        supplier_cnpj = utils.mask_cnpj("%014d" % root.CNPJ)

        dfe = self.env["l10n_br_fiscal_dfe.dfe"].create(
            {
                "access_key": nfe_key,
                "emitter": root.xNome,
                "operation_type": str(root.tpNF),
                "document_amount": root.vNF,
                "document_state": str(root.cSitNFe),
                "inclusion_datetime": datetime.now(),
                "vat": supplier_cnpj,
                "ie": root.IE,
                "emission_datetime": datetime.strptime(
                    str(root.dhEmi)[:19], "%Y-%m-%dT%H:%M:%S"
                ),
                "company_id": self.company_id.id,
                "dfe_monitor_id": self.id,
                "dfe_nfe_document_type": "dfe_nfe_summary",
                "nsu": nsu,
            }
        )

        if self.auto_manifest_nfe:
            mde = self.env["l10n_br_nfe.md_event"].create(
                {
                    "access_key": nfe_key,
                    "event_type": "ciente",
                    "company_id": self.company_id.id,
                    "document_type": "nfe",
                    "state": "draft",
                }
            )
            mde.action_confirm()

        dfe_document_id.dfe_ids = [(4, dfe.id)]
        return dfe

    @api.model
    def _create_dfe_from_resEvento(self, root, nsu):
        nfe_key = root.chNFe
        access_key = self._get_or_create_document(nfe_key)
        supplier_cnpj = utils.mask_cnpj("%014d" % root.CNPJ)

        dfe = self.env["l10n_br_fiscal_dfe.dfe"].create(
            {
                "access_key": nfe_key,
                "inclusion_datetime": datetime.now(),
                "vat": supplier_cnpj,
                "emission_datetime": datetime.strptime(
                    str(root.dhEvento)[:19], "%Y-%m-%dT%H:%M:%S"
                ),
                "company_id": self.company_id.id,
                "dfe_monitor_id": self.id,
                "event_type_dfe": str(root.tpEvento),
                "dfe_nfe_document_type": "dfe_nfe_event",
                "nsu": nsu,
            }
        )

        access_key.dfe_ids = [(4, dfe.id)]
        return dfe

    @api.model
    def _create_dfe_from_procEventoNFe(self, root, nsu):
        nfe_key = root.evento.infEvento.chNFe

        dfe_document_id = self._get_or_create_document(nfe_key)

        supplier_cnpj = utils.mask_cnpj("%014d" % root.evento.infEvento.CNPJ)

        dfe = self.env["l10n_br_fiscal_dfe.dfe"].create(
            {
                "access_key": nfe_key,
                "inclusion_datetime": datetime.now(),
                "vat": supplier_cnpj,
                "emission_datetime": datetime.strptime(
                    str(root.evento.infEvento.dhEvento)[:19], "%Y-%m-%dT%H:%M:%S"
                ),
                "company_id": self.company_id.id,
                "dfe_monitor_id": self.id,
                "dfe_nfe_document_type": "dfe_nfe_event",  # TODO: tipo de DFe evento?
                "nsu": nsu,
            }
        )

        dfe_document_id.dfe_ids = [(4, dfe.id)]
        return dfe

    def _get_or_create_document(self, nfe_key):
        Document = self.env["l10n_br_fiscal_dfe.document"]
        domain = [
            ("access_key", "=", nfe_key),
            ("company_id", "=", self.company_id.id),
        ]

        document = Document.search(domain, limit=1)
        if not document:
            document = Document.create(
                {
                    "access_key": nfe_key,
                    "company_id": self.company_id.id,
                    "dfe_monitor_id": self.id,
                }
            )
        return document

    @api.model
    def find_dfe_by_key(self, key):
        dfe_id = self.env["l10n_br_fiscal_dfe.dfe"].search([("key", "=", key)])
        if not dfe_id:
            return False

        if dfe_id not in self.dfe_ids:
            dfe_id.dfe_monitor_id = self.id
        return dfe_id

    def import_documents(self):
        for record in self:
            record.dfe_ids.import_document_multi()

    @api.model
    def parse_procNFe(self, xml):
        binding = TnfeProc.from_xml(xml.read().decode())
        return self.env["l10n_br_fiscal.document"].import_binding_nfe(binding)

    _sql_constraints = [
        (
            "unique_company_id",
            "unique(company_id)",
            "A DF-e Monitor already exists for this company",
        ),
    ]
