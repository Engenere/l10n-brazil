# Copyright (C) 2023 KMEE Informatica LTDA
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl)

from datetime import datetime

from lxml import objectify
from nfelib.nfe.bindings.v4_0.leiaute_nfe_v4_00 import TnfeProc

from odoo import api, fields, models

from odoo.addons.l10n_br_fiscal_dfe.tools import utils


class DFeMonitor(models.Model):
    _inherit = "l10n_br_fiscal.dfe_monitor"

    dfe_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.dfe",
        inverse_name="dfe_monitor_id",
        string="Documentos Fiscais Eletrônicos",
    )

    dfe_nfe_complete_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.dfe",
        inverse_name="dfe_monitor_id",
        domain=[("dfe_nfe_document_type", "=", "dfe_nfe_complete")],
        string="NF-e Completa",
    )

    dfe_nfe_summary_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.dfe",
        inverse_name="dfe_monitor_id",
        domain=[("dfe_nfe_document_type", "=", "dfe_nfe_summary")],
        string="Resumo da NF-e",
    )

    dfe_nfe_event_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.dfe",
        inverse_name="dfe_monitor_id",
        domain=[("dfe_nfe_document_type", "=", "dfe_nfe_event")],
        string="Evento da NF-e",
    )

    def _process_distribution(self, result):
        for doc in result.resposta.loteDistDFeInt.docZip:
            xml = utils.parse_gzip_xml(doc.valueOf_).read()
            root = objectify.fromstring(xml)

            dfe_id = self.env["l10n_br_fiscal.dfe"].search(
                [
                    ("nsu", "=", utils.format_nsu(doc.NSU)),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )

            schema_type = doc.schema.split("_")[0]
            if schema_type == "procNFe":
                self._create_dfe_from_procNFe(root)
            elif schema_type == "resNFe":
                self._create_dfe_from_resNFe(root)
            elif schema_type == "resEvento":
                self._create_dfe_from_resEvento(root)
                if dfe_id:
                    dfe_id.nsu = doc.NSU
                    dfe_id.create_xml_attachment(xml)

    @api.model
    def _create_dfe_from_procNFe(self, root):
        nfe_key = root.protNFe.infProt.chNFe
        dfe_id = self.find_dfe_by_key(nfe_key)
        if dfe_id:
            return dfe_id

        supplier_cnpj = utils.mask_cnpj("%014d" % root.NFe.infNFe.emit.CNPJ)
        partner = self.env["res.partner"].search([("cnpj_cpf", "=", supplier_cnpj)])

        cfop_codes = []
        for det in root.NFe.infNFe.det:
            cfop_code = str(det.prod.CFOP)
            if cfop_code not in cfop_codes:
                cfop_codes.append(cfop_code)
        cfop_records = self.env["l10n_br_fiscal.cfop"].search(
            [("code", "in", cfop_codes)]
        )
        return self.env["l10n_br_fiscal.dfe"].create(
            {
                "number": root.NFe.infNFe.ide.nNF,
                "emitter": root.NFe.infNFe.emit.xNome,
                "key": nfe_key,
                "operation_type": str(root.NFe.infNFe.ide.tpNF),
                "document_value": root.NFe.infNFe.total.ICMSTot.vNF,
                "inclusion_datetime": datetime.now(),
                "cnpj_cpf": supplier_cnpj,
                "ie": root.NFe.infNFe.emit.IE,
                "partner_id": partner.id,
                "emission_datetime": datetime.strptime(
                    str(root.NFe.infNFe.ide.dhEmi)[:19],
                    "%Y-%m-%dT%H:%M:%S",
                ),
                "company_id": self.company_id.id,
                "inclusion_mode": "Verificação agendada",
                "dfe_monitor_id": self.id,
                "cfop_ids": [(6, 0, cfop_records.ids)],
                "dfe_nfe_document_type": "dfe_nfe_complete",
            }
        )

    @api.model
    def _create_dfe_from_resNFe(self, root):
        nfe_key = root.chNFe
        dfe_id = self.find_dfe_by_key(nfe_key)
        if dfe_id:
            return dfe_id

        supplier_cnpj = utils.mask_cnpj("%014d" % root.CNPJ)
        partner_id = self.env["res.partner"].search([("cnpj_cpf", "=", supplier_cnpj)])

        return self.env["l10n_br_fiscal.dfe"].create(
            {
                "key": nfe_key,
                "emitter": root.xNome,
                "operation_type": str(root.tpNF),
                "document_value": root.vNF,
                "document_state": str(root.cSitNFe),
                "inclusion_datetime": datetime.now(),
                "cnpj_cpf": supplier_cnpj,
                "ie": root.IE,
                "partner_id": partner_id.id,
                "emission_datetime": datetime.strptime(
                    str(root.dhEmi)[:19], "%Y-%m-%dT%H:%M:%S"
                ),
                "company_id": self.company_id.id,
                "inclusion_mode": "Verificação agendada - manifestada por outro app",
                "dfe_monitor_id": self.id,
                "dfe_nfe_document_type": "dfe_nfe_summary",
            }
        )

    @api.model
    def _create_dfe_from_resEvento(self, root):
        nfe_key = root.chNFe
        dfe_id = self.find_dfe_by_key(nfe_key)
        if dfe_id:
            return dfe_id

        supplier_cnpj = utils.mask_cnpj("%014d" % root.CNPJ)
        partner_id = self.env["res.partner"].search([("cnpj_cpf", "=", supplier_cnpj)])

        return self.env["l10n_br_fiscal.dfe"].create(
            {
                "key": nfe_key,
                "inclusion_datetime": datetime.now(),
                "cnpj_cpf": supplier_cnpj,
                "partner_id": partner_id.id,
                "emission_datetime": datetime.strptime(
                    str(root.dhEvento)[:19], "%Y-%m-%dT%H:%M:%S"
                ),
                "company_id": self.company_id.id,
                "inclusion_mode": "Verificação agendada - manifestada por outro app",
                "dfe_monitor_id": self.id,
                "dfe_nfe_document_type": "dfe_nfe_event",
            }
        )

    @api.model
    def find_dfe_by_key(self, key):
        dfe_id = self.env["l10n_br_fiscal.dfe"].search([("key", "=", key)])
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
