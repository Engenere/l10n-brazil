# Copyright (C) 2009 - TODAY Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_br_fiscal.constants.fiscal import SITUACAO_EDOC_EM_DIGITACAO


class FiscalDocument(models.Model):
    _inherit = "l10n_br_fiscal.document"

    move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="fiscal_document_id",
        string="Invoices",
    )

    def modified(self, fnames, create=False, before=False):
        """
        Modifying a dummy fiscal document (no document_type_id) should not recompute
        any account.move related to the same dummy fiscal document.
        """
        filtered = self.filtered(
            lambda rec: isinstance(rec.id, models.NewId) or rec.document_type_id
        )
        return super(FiscalDocument, filtered).modified(fnames, create, before)

    def _modified_triggers(self, tree, create=False):
        """
        Modifying a dummy fiscal document (no document_type_id) should not recompute
        any account.move related to the same dummy fiscal document.
        """
        filtered = self.filtered(
            lambda rec: isinstance(rec.id, models.NewId) or rec.document_type_id
        )
        return super(FiscalDocument, filtered)._modified_triggers(tree, create)

    fiscal_line_ids = fields.One2many(
        copy=False,
    )

    def unlink(self):
        non_draft_documents = self.filtered(
            lambda d: d.state != SITUACAO_EDOC_EM_DIGITACAO
        )

        if non_draft_documents:
            UserError(
                _("You cannot delete a fiscal document " "which is not draft state.")
            )
        return super().unlink()
