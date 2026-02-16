# Copyright 2026 Engenere
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "L10n BR Fiscal Tax JSON",
    "summary": "Consolida campos de impostos fiscais em um campo JSON para performance",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Engenere, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-brazil",
    "depends": ["l10n_br_fiscal", "l10n_br_purchase"],
    "pre_init_hook": "_pre_init_populate_tax_data",
}
