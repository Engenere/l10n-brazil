# Copyright (C) 2025-Today - Engenere (<https://engenere.one>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
import re
from io import BytesIO

from brazilfiscalreport.danfe import Danfe

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..constants.dfe import SITUACAO_NFE

EVENT_TYPE_MAP = {
    "210200": "Confirmada operação",
    "210210": "Ciente da Operação",
    "210220": "Desconhecimento da Operação",
    "210240": "Operação não realizada",
}


class L10nBrFiscalDfeDocument(models.Model):
    _name = "l10n_br_fiscal_dfe.document"
    _description = "Fiscal document from distribution service"
    _order = "id desc"

    _sql_constraints = [
        (
            "access_key_company_uniq",
            "unique(access_key, company_id)",
            "A DFe with this access key already exists for this company.",
        ),
    ]

    access_key = fields.Char(size=44, required=True)

    dfe_ids = fields.One2many(
        comodel_name="l10n_br_fiscal_dfe.dfe",
        inverse_name="dfe_document_id",
        string="DF-e records",
    )

    emitter = fields.Char(compute="_compute_dfe_info")

    vat = fields.Char(related="dfe_ids.vat")

    document_amount = fields.Float(
        string="Document Total Value", digits=(18, 2), compute="_compute_dfe_info"
    )

    document_state = fields.Selection(
        selection=SITUACAO_NFE, compute="_compute_dfe_info"
    )

    document_number = fields.Float(compute="_compute_dfe_info")

    document_emission_date = fields.Datetime(compute="_compute_dfe_info")

    serie = fields.Char(compute="_compute_dfe_info")

    color_status = fields.Selection(
        [
            ("green", "NF-e Completa"),
            ("blue", "Resumo da NF-e"),
            ("normal", "Evento da NF-e"),
        ],
        compute="_compute_color_status",
    )

    manifestation_status = fields.Selection(
        selection=[
            ("ciente", "Ciente da Operação"),
            ("confirmado", "Confirmada operação"),
            ("desconhecido", "Desconhecimento"),
            ("nao_realizado", "Não realizado"),
            ("sem_manifestacao", "Sem manifestação"),
        ],
        compute="_compute_manifestation_status",
    )

    manifestations_ids = fields.One2many(
        comodel_name="l10n_br_nfe.md_event",
        compute="_compute_manifestations_ids",
        string="Manifestations",
    )

    cfop_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.cfop",
        string="CFOPs",
        compute="_compute_cfop_ids",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company.id,
        index=True,
    )

    is_own_document = fields.Boolean(
        string="Own Document",
        compute="_compute_is_own_document",
        store=True,
        help="True when the emitter CNPJ in the access key matches the company CNPJ.",
    )

    @api.depends("access_key", "company_id.vat")
    def _compute_is_own_document(self):
        for record in self:
            key = record.access_key or ""
            company_cnpj = re.sub("[^0-9]", "", record.company_id.vat or "")
            if len(key) == 44 and company_cnpj:
                record.is_own_document = key[6:20] == company_cnpj
            else:
                record.is_own_document = False

    @api.depends("dfe_ids.cfop_ids")
    def _compute_cfop_ids(self):
        for record in self:
            record.cfop_ids = record.dfe_ids.mapped("cfop_ids")

    def _compute_dfe_info(self):
        for record in self:
            dfe_ids = record.dfe_ids

            complete = dfe_ids.filtered(
                lambda d: d.dfe_nfe_document_type == "dfe_nfe_complete"
            )
            summary = dfe_ids.filtered(
                lambda d: d.dfe_nfe_document_type == "dfe_nfe_summary"
            )

            dfe = (
                (complete and complete[0])
                or (summary and summary[0])
                or (dfe_ids and dfe_ids[0])
                or False
            )

            if dfe:
                record.emitter = dfe.emitter
                record.document_amount = dfe.document_amount
                record.document_state = dfe.document_state
                record.document_number = dfe.document_number
                record.document_emission_date = dfe.emission_datetime
                record.serie = dfe.serie
            else:
                record.emitter = False
                record.document_amount = 0.0
                record.document_state = False
                record.document_number = 0.0
                record.document_emission_date = False
                record.serie = False

    def _compute_manifestation_status(self):
        for record in self:
            latest = self.env["l10n_br_nfe.md_event"].search(
                [
                    ("access_key", "=", record.access_key),
                    ("state", "=", "done"),
                ],
                order="id desc",
                limit=1,
            )
            record.manifestation_status = (
                latest.event_type if latest else "sem_manifestacao"
            )

    @api.depends("access_key")
    def _compute_manifestations_ids(self):
        for record in self:
            manifestations = self.env["l10n_br_nfe.md_event"].search(
                [("access_key", "=", record.access_key)]
            )
            record.manifestations_ids = manifestations

    @api.depends("dfe_ids.dfe_nfe_document_type")
    def _compute_color_status(self):
        for record in self:
            types = record.dfe_ids.mapped("dfe_nfe_document_type")
            if "dfe_nfe_complete" in types:
                record.color_status = "green"
            elif "dfe_nfe_summary" in types:
                record.color_status = "blue"
            else:
                record.color_status = "normal"

    def name_get(self):
        return [(record.id, record.access_key) for record in self]

    def action_download_xml(self):
        complete_dfe_ids = self.dfe_ids.filtered(
            lambda dfe: dfe.dfe_nfe_document_type == "dfe_nfe_complete"
        )
        if complete_dfe_ids:
            return complete_dfe_ids.action_download_xml()
        raise UserError(
            _("It is only possible to download XML when DF-e is completed.")
        )

    def make_pdf(self):
        complete_dfe_ids = self.dfe_ids.filtered(
            lambda dfe: dfe.dfe_nfe_document_type == "dfe_nfe_complete"
        )

        if not complete_dfe_ids:
            raise UserError(_("No DF-e with 'DF-e complete' type found."))

        complete_dfe = complete_dfe_ids[0]
        attachment = complete_dfe.attachment_id
        nfe_xml = base64.b64decode(attachment.datas)
        danfe = Danfe(xml=nfe_xml)

        tmpDanfe = BytesIO()
        danfe.output(tmpDanfe)
        danfe_file = tmpDanfe.getvalue()
        tmpDanfe.close()

        pdf_attachment = self.env["ir.attachment"].create(
            {
                "name": f"DANFE{complete_dfe.access_key}.pdf",
                "type": "binary",
                "datas": base64.b64encode(danfe_file),
                "res_model": self._name,
                "res_id": complete_dfe.id,
                "mimetype": "application/pdf",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{pdf_attachment.id}?download=true",
            "target": "self",
        }

    # TODO migrar pro módulo l10n_br_nfe_dfe
    def create_nfe_md_action(self):
        self.ensure_one()
        return {
            "name": _("Manifestação do Destinatário da NF-e"),
            "type": "ir.actions.act_window",
            "res_model": "nfe_recipient_manifestation_event.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_access_key": self.access_key,
            },
        }

    def import_document(self):
        complete_dfe_ids = self.dfe_ids.filtered(
            lambda dfe: dfe.dfe_nfe_document_type == "dfe_nfe_complete"
        )
        if complete_dfe_ids:
            return complete_dfe_ids.import_document()
        raise UserError(_("You can only import the NF-e when the DF-e is completed."))

    # ── Tree header actions (delegate to company) ───────────────────────

    def action_search_all_dfe(self):
        return self.env.company.action_document_distribution()

    def action_search_specific_dfe(self):
        return self.env.company.action_search_specific()
