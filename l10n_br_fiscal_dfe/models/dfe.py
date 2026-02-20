# Copyright 2026 Engenere (<https://engenere.one>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
import logging

from lxml import etree

from odoo import _, api, fields, models

from ..constants.dfe import OPERATION_TYPE

_logger = logging.getLogger(__name__)

EVENT_TYPE_LABELS = {
    "210200": "Confirmação da Operação",
    "210210": "Ciência da Operação",
    "210220": "Desconhecimento da Operação",
    "210240": "Operação não Realizada",
    "110110": "Carta de Correção",
    "110111": "Cancelamento",
    "110112": "Cancelamento por Substituição",
    "110140": "EPEC",
}

DFE_DESCRIPTION_MAP = {
    "procNFe": "XML NF-e completo (procNFe) via distribuição DF-e",
    "resNFe": "Resumo de NF-e (resNFe) via distribuição DF-e",
    "procEventoNFe": "XML de evento de NF-e (procEventoNFe) via distribuição DF-e",
    "resEvento": "Resumo de evento de NF-e (resEvento) via distribuição DF-e",
}


class DFe(models.Model):
    _name = "l10n_br_fiscal_dfe.dfe"
    _description = "DF-e"
    _order = "id desc"

    dfe_document_id = fields.Many2one(
        comodel_name="l10n_br_fiscal_dfe.document", string="DF-e Document"
    )

    access_key = fields.Char(size=44)

    nsu = fields.Char(string="NSU", size=25, index=True)

    schema_type = fields.Char(
        help="Type of the DF-e document according to the XML schema.",
    )

    operation_type = fields.Selection(
        selection=OPERATION_TYPE,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
    )

    dfe_nfe_document_type = fields.Selection(
        selection=[
            ("dfe_nfe_complete", "NF-e Completa"),
            ("dfe_nfe_summary", "Resumo da NF-e"),
            ("dfe_nfe_event", "Evento da NF-e"),
        ],
        string="DF-e Type (NF-e)",
    )

    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        help="XML Attachment stored in Odoo.",
    )

    xml_pretty = fields.Text(string="XML Pretty", compute="_compute_xml_pretty")

    event_type_dfe = fields.Char(string="Event Type")

    event_type_dfe_label = fields.Char(
        string="Event",
        compute="_compute_event_type_dfe_label",
    )

    @api.depends("event_type_dfe")
    def _compute_event_type_dfe_label(self):
        for rec in self:
            code = rec.event_type_dfe
            if not code:
                rec.event_type_dfe_label = False
            elif code in EVENT_TYPE_LABELS:
                rec.event_type_dfe_label = EVENT_TYPE_LABELS[code]
            else:
                rec.event_type_dfe_label = _("Other (%(code)s)", code=code)

    def name_get(self):
        result = []
        for rec in self:
            document_type = dict(rec._fields["dfe_nfe_document_type"].selection).get(
                rec.dfe_nfe_document_type
            )
            result.append(
                (
                    rec.id,
                    f"{rec.access_key} - {document_type}",
                )
            )
        return result

    def create_xml_attachment(self, xml):
        self.sudo().attachment_id = self.env["ir.attachment"].create(
            {
                "name": f"{self.schema_type}{self.access_key}.xml",
                "datas": base64.b64encode(xml),
                "description": DFE_DESCRIPTION_MAP.get(self.schema_type),
                "res_model": self._name,
                "res_id": self.id,
            }
        )

    def action_download_xml(self):
        if len(self) == 1:
            return self.download_attachment(self.attachment_id)

        compressed_attachment_id = (
            self.env["l10n_br_fiscal.attachment"]
            .create([])
            .build_compressed_attachment(self.mapped("attachment_id"))
        )
        return self.download_attachment(compressed_attachment_id)

    def download_attachment(self, attachment_id):
        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/web/content/{attachment_id.id}"
                f"/{attachment_id.name}?download=true"
            ),
            "target": "self",
        }

    def import_document(self):
        self.ensure_one()
        try:
            document = self.company_id._dfe_download_document(self.access_key)
            self.company_id._dfe_parse_xml_document(document)
        except Exception as exc:
            self.company_id._dfe_log(
                _("Error importing document: \n\n %(error)s", error=exc),
                log_type="error",
            )

    def import_document_multi(self):
        for rec in self:
            rec.import_document()

    @api.depends("attachment_id")
    def _compute_xml_pretty(self):
        for rec in self:
            rec.xml_pretty = False
            data = rec.attachment_id.with_context(bin_size=False).datas
            if not data:
                continue
            xml_file = base64.b64decode(data)
            root = etree.fromstring(xml_file)
            rec.xml_pretty = etree.tostring(
                root,
                pretty_print=True,
                encoding="unicode",
            )
