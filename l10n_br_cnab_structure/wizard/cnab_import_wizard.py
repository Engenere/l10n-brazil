# Copyright 2022 Engenere
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from io import StringIO
import base64


class CNABImportWizard(models.TransientModel):

    _name = "cnab.import.wizard"
    _description = "CNAB Import Wizard"

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        help="Only journals where the CNAB Import is allowed.",
        required=True,
    )
    bank_account_cnab_id = fields.Many2one(
        comodel_name="account.account",
        related="journal_id.default_account_id",
        readonly=True,
    )
    return_file = fields.Binary("Return File")
    filename = fields.Char()
    type = fields.Selection(
        [
            ("inbound", "Inbound Payment"),
            ("outbound", "Outbound Payment"),
        ],
        string="Type",
    )

    bank_id = fields.Many2one(comodel_name="res.bank", related="journal_id.bank_id")
    payment_method_ids = fields.Many2many(
        comodel_name="account.payment.method", compute="_compute_payment_method_ids"
    )
    cnab_structure_id = fields.Many2one(
        comodel_name="l10n_br_cnab.structure",
        domain="[('bank_id', '=', bank_id),('payment_method_id', 'in', payment_method_ids),('state', '=', 'approved')]",
    )
    cnab_format = fields.Char(
        related="cnab_structure_id.cnab_format",
    )

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        structure_obj = self.env["l10n_br_cnab.structure"]
        structure_ids = structure_obj.search(
            [
                ("bank_id", "=", self.bank_id.id),
                ("payment_method_id", "in", self.payment_method_ids.ids),
                ("state", "=", "approved"),
            ]
        )
        if len(structure_ids):
            self.cnab_structure_id = structure_ids[0]
        else:
            self.cnab_structure_id = [(5, 0, 0)]

    @api.depends("journal_id", "type")
    def _compute_payment_method_ids(self):
        for record in self:
            if record.type == "inbound":
                record.payment_method_ids = record.journal_id.inbound_payment_method_ids
            elif record.type == "outbound":
                record.payment_method_ids = (
                    record.journal_id.outbound_payment_method_ids
                )
            else:
                record.payment_method_ids = [(5, 0, 0)]

    def _get_conf_positions_240(self):
        "Return Start and End position of configuration files. Values pre defined: bank, record_type, batch, payment_way, detail or segment."
        structure_id = self.cnab_structure_id
        start_pos = {
            "bank": structure_id.conf_bank_start_pos - 1,
            "record_type": structure_id.conf_record_type_start_pos - 1,
            "batch": structure_id.conf_batch_start_pos - 1,
            "payment_way": structure_id.conf_payment_way_start_pos - 1,
            "detail": structure_id.conf_detail_start_pos - 1,
            "segment": structure_id.conf_segment_start_pos - 1,
        }
        end_pos = {
            "bank": structure_id.conf_bank_end_pos,
            "record_type": structure_id.conf_record_type_end_pos,
            "batch": structure_id.conf_batch_end_pos,
            "payment_way": structure_id.conf_payment_way_end_pos,
            "detail": structure_id.conf_detail_end_pos,
            "segment": structure_id.conf_segment_end_pos,
        }
        return start_pos, end_pos

    def _get_record_types(self):
        structure_id = self.cnab_structure_id
        record_types = {
            "header_file": structure_id.record_type_file_header_id,
            "trailer_file": structure_id.record_type_file_trailer_id,
            "header_batch": structure_id.record_type_batch_header_id,
            "trailer_batch": structure_id.record_type_batch_trailer_id,
            "detail": structure_id.record_type_detail_id,
        }
        return record_types

    def _get_content(self, line, conf_field):
        """
        Get content of configuration field from CNAB line. Values pre defined: bank, record_type, batch, payment_way, detail or segment.
        """
        start_pos, end_pos = self._get_conf_positions_240()
        return line[start_pos[conf_field] : end_pos[conf_field]]

    def _get_lines_from_file(self, file):
        file = base64.b64decode(self.return_file)
        string = StringIO(file.decode("utf-8"))
        lines = string.readlines()
        lines = [line.replace("\r\n", "") for line in lines]
        return lines

    def _check_bank(self, line):
        bank_line = self._get_content(line, "bank")
        bank_structure = self.cnab_structure_id.bank_id.code_bc
        if bank_line != bank_structure:
            raise UserError(
                _(
                    f"The bank {bank_line} from file is different of the bank os selected structure({bank_structure})."
                )
            )

    def _check_cnab_240(self, lines):
        for index, line in enumerate(lines):
            if len(line) != 240:
                raise UserError(
                    _(f"Number of positions of line {index+1} is different of 240.")
                )

    def _filter_lines(self, lines, conf_field, value):
        """
        Returns CNAB lines filtered by specific values of a configuration field. This fields are set in cnab structure.

        Args:
            lines (List): A list of strings of CNAB lines.
            conf_field (string): The name of the configuration field: bank, record_type, batch, payment_way, detail or segment.
            value (string, int): The value of conf_field to filter.
        Returns:
            List: A list of CNAB lines.
        """
        filtered_lines = list(
            filter(
                lambda line: self._get_content(line, conf_field) == str(value),
                lines,
            )
        )
        return filtered_lines

    def _filter_lines_from_type(self, lines, type_name):
        """
        Returns CNAB lines filtered by type. This types are set in cnab structure.

        Args:
            lines (List): A list of strings of CNAB lines.
            type_name (string): Name of type: header_file, trailer_file, header_batch, trailer_batch or detail.
        Returns:
            List: A list of CNAB lines.
        """
        record_types = self._get_record_types()
        filtered_lines = self._filter_lines(
            lines, "record_type", record_types[type_name]
        )

        return filtered_lines

    def _get_unique_batch_list(self, lines):
        batch_list = []
        for line in lines:
            batch = self._get_content(line, "batch")
            # Ignore batches from header and trailer of file, they will always be 0000 and 9999.
            # If there is an exception, it must be handled.
            if batch not in ["0000", "9999"]:
                batch_list.append(batch)
        return list(set(batch_list))

    def _get_unique_datail_list(self, lines):
        detail_list = []
        for line in lines:
            detail = self._get_content(line, "detail")
            detail_list.append(detail)
        return list(set(detail_list))

    def _get_segments(self, segment_lines, batch_template):
        segments = []
        for s in segment_lines:
            segment_code = self._get_content(s, "segment")
            line_template = batch_template.line_ids.filtered(
                lambda line: line.type == "segment"
                and line.segment_code == segment_code
            )
            segment = {"raw_line": s, "line_template": line_template}
            segments.append(segment)
        return segments

    def _get_details(self, detail_lines, batch_template):
        detail_list = self._get_unique_datail_list(detail_lines)
        details = []

        for d in detail_list:
            segment_lines = self._filter_lines(detail_lines, "detail", d)
            segments = self._get_segments(segment_lines, batch_template)
            details.append(segments)

        return details

    def _get_payment_way(self, code):
        batch_domain = [
            ("cnab_structure_id", "=", self.cnab_structure_id.id),
            ("code", "=", code),
        ]
        return self.env["cnab.payment.way"].search(batch_domain, limit=1)

    def _get_batch_template(self, payment_way_code):
        cnab_payment_way_id = self._get_payment_way(payment_way_code)
        batch_domain = [
            ("cnab_structure_id", "=", self.cnab_structure_id.id),
            ("cnab_payment_way_ids", "in", [cnab_payment_way_id.id]),
        ]
        return self.env["l10n_br_cnab.batch"].search(batch_domain, limit=1)

    def _get_batches(self, lines):
        batch_list = self._get_unique_batch_list(lines)
        batches = []

        for b in batch_list:
            batch = {}
            batch_lines = self._filter_lines(lines, "batch", b)

            batch_header_raw_line = self._filter_lines_from_type(
                batch_lines, "header_batch"
            )[0]
            payment_way_code = self._get_content(batch_header_raw_line, "payment_way")
            batch_template = self._get_batch_template(payment_way_code)

            batch["header_batch_line"] = {
                "raw_line": batch_header_raw_line,
                "line_template": batch_template.line_ids.filtered(
                    lambda line: line.type == "header"
                ),
            }
            batch["trailer_batch_line"] = {
                "raw_line": self._filter_lines_from_type(batch_lines, "trailer_batch")[
                    0
                ],
                "line_template": batch_template.line_ids.filtered(
                    lambda line: line.type == "trailer"
                ),
            }

            detail_lines = self._filter_lines_from_type(batch_lines, "detail")
            batch["details"] = self._get_details(detail_lines, batch_template)

            batches.append(batch)

        return batches

    def _get_data_from_file(self):
        lines = self._get_lines_from_file(self.return_file)
        self._check_bank(lines[0])
        self._check_cnab_240(lines)
        data = {}
        data["header_file_line"] = {
            "raw_line": self._filter_lines_from_type(lines, "header_file")[0],
            "line_template": self.cnab_structure_id.line_ids.filtered(
                lambda line: not line.batch_id and line.type == "header"
            ),
        }
        data["trailer_file_line"] = {
            "raw_line": self._filter_lines_from_type(lines, "trailer_file")[0],
            "line_template": self.cnab_structure_id.line_ids.filtered(
                lambda line: not line.batch_id and line.type == "trailer"
            ),
        }
        data["batches"] = self._get_batches(lines)
        return data

    def _create_return_logs(self, data):
        # TODO
        pass

    def _import_cnab_240(self):
        data = self._get_data_from_file()
        return_logs = self._create_return_logs(data)

        return return_logs

    def import_cnab(self):
        if self.cnab_format == "240":
            return_logs = self._import_cnab_240()
        else:
            raise UserError(_(f"CNAB Format {self.cnab_format} not implemented."))

        action = {
            # TODO
        }

        return False
