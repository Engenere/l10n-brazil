# Copyright 2020 KMEE INFORMATICA LTDA
# Copyright 2026 Engenere (<https://engenere.one>).
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl)

import base64
import io
import logging
import tarfile

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Attachment(models.TransientModel):
    _name = "l10n_br_fiscal.attachment"
    _description = "Fiscal Document Attachment"

    attachment = fields.Binary(readonly=True)

    file_name = fields.Char(default="attachments")

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
    )

    @api.model
    def build_compressed_attachment(self, record_ids=None):
        """Compress received attachments and return them as a single attachment.

        :param record_ids: A recordset of ir.attachment records, or any records
            whose related ir.attachments should be compressed.
        :return: A single ir.attachment containing all received attachments
            compressed in a tar.gz file.
        """
        self.attachment_ids = self._records_to_attachments(record_ids)

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for attachment in self.attachment_ids:
                data = base64.b64decode(
                    attachment.with_context(bin_size=False).datas or b""
                )
                if not data:
                    _logger.warning("Empty attachment skipped: %s", attachment.name)
                    continue
                info = tarfile.TarInfo(name=attachment.name or "unknown")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

        return self.env["ir.attachment"].create(
            {
                "name": "attachments.tar.gz",
                "type": "binary",
                "datas": base64.b64encode(buf.getvalue()),
                "res_model": "l10n_br_fiscal.attachment",
                "res_id": self.id,
            }
        )

    @api.model
    def _records_to_attachments(self, record_ids):
        attachment_obj = self.env["ir.attachment"]
        attachment_ids = record_ids

        if isinstance(record_ids, list) and len(record_ids):
            attachs = self.env[record_ids[0]._name]
            for record in record_ids:
                attachs += record
            attachment_ids = attachs

        if attachment_ids._name != "ir.attachment":
            ids = attachment_obj
            for record in attachment_ids:
                ids += attachment_obj.search([("res_id", "=", record.id)])
            attachment_ids = ids

        return attachment_ids
