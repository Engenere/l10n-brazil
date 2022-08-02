# Copyright 2022 Engenere
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CNABField(models.Model):

    _name = "l10n_br_cnab.line.field"
    _description = "Fields in CNAB lines."

    name = fields.Char(readonly=True, states={"draft": [("readonly", "=", False)]})
    meaning = fields.Char(readonly=True, states={"draft": [("readonly", "=", False)]})
    cnab_line_id = fields.Many2one(
        "l10n_br_cnab.line",
        readonly=True,
        ondelete="cascade",
        required=True,
        states={"draft": [("readonly", "=", False)]},
    )
    start_pos = fields.Integer(
        string="Start Position",
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )
    end_pos = fields.Integer(
        string="End Position",
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )
    type = fields.Selection(
        [
            ("alpha", _("Alphanumeric")),
            ("num", _("Numeric")),
        ],
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )
    related_field_id = fields.Many2one(
        "ir.model.fields", readonly=True, states={"draft": [("readonly", "=", False)]}
    )
    default_value = fields.Char(
        readonly=True, states={"draft": [("readonly", "=", False)]}
    )
    notes = fields.Char(readonly=True, states={"draft": [("readonly", "=", False)]})
    size = fields.Integer(compute="_compute_size")

    state = fields.Selection(
        selection=[("draft", "Draft"), ("review", "Review"), ("approved", "Approved")],
        readonly=True,
        default="draft",
    )

    @api.depends("start_pos", "end_pos")
    def _compute_size(self):
        for f in self:
            f.size = f.end_pos - f.start_pos + 1

    def unlink(self):
        lines = self.filtered(lambda l: l.state != "draft")
        if lines:
            raise UserError(_("You cannot delete an CNAB Field which is not draft !"))
        return super(CNABField, self).unlink()

    def action_review(self):
        self.write({"state": "review"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_draft(self):
        self.write({"state": "draft"})

    def check_field(self):
        if self.start_pos > self.end_pos:
            raise UserError(
                _(
                    "%s in %s: Start position is greater than end position."
                    % (self.name, self.cnab_line_id)
                )
            )
