# Copyright (C) 2013  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    'name': 'Brazilian Fiscal',
    'summary': 'Brazilian fiscal core module.',
    'category': 'Localisation',
    'license': 'AGPL-3',
    'author': 'Akretion, '
              'Odoo Community Association (OCA)',
    'website': 'http://github.com/OCA/l10n-brazil',
    'version': '12.0.1.0.0',
    'depends': [
        'uom',
        'decimal_precision',
        'product',
        'l10n_br_base'
    ],
    'data': [
        # security
        'security/fiscal_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/l10n_br_fiscal_data.xml',
        'data/uom_data.xml',
        'data/product_data.xml',
        'data/l10n_br_fiscal.tax.group.csv',
        'data/l10n_br_fiscal.document.type.csv',
        'data/l10n_br_fiscal.product.genre.csv',
        'data/l10n_br_fiscal.cst.csv',
        'data/l10n_br_fiscal.tax.csv',
        'data/l10n_br_fiscal.tax.pis.cofins.csv',
        'data/partner_profile_data.xml',
        'data/l10n_br_fiscal_server_action.xml',
        'data/ir_cron.xml',

        # Views
        'views/cnae_view.xml',
        'views/cfop_view.xml',
        'views/comment_view.xml',
        'views/cst_view.xml',
        'views/tax_group_view.xml',
        'views/tax_view.xml',
        'views/tax_pis_cofins_view.xml',
        'views/tax_pis_cofins_base_view.xml',
        'views/tax_pis_cofins_credit_view.xml',
        'views/tax_ipi_guideline_view.xml',
        'views/ncm_view.xml',
        'views/nbs_view.xml',
        'views/service_type_view.xml',
        'views/cest_view.xml',
        'views/product_genre_view.xml',
        'views/document_type_view.xml',
        'views/document_serie_view.xml',
        'views/certificate_view.xml',
        'views/simplified_tax_view.xml',
        'views/simplified_tax_range_view.xml',
        'views/operation_view.xml',
        'views/operation_line_view.xml',
        'views/product_template_view.xml',
        'views/product_product_view.xml',
        'views/tax_estimate_view.xml',
        'views/partner_profile_view.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/document_view.xml',
        'views/document_line_view.xml',
        'views/res_config_settings_view.xml',
        'views/l10n_br_fiscal_action.xml',
        'views/l10n_br_fiscal_menu.xml',

        # 'data/l10n_br_account_product_sequence.xml',
        # 'data/l10n_br_account_data.xml',
        # 'data/l10n_br_account_product_data.xml',
        # 'data/l10n_br_tax.icms_partition.csv',
        # 'views/l10n_br_account_product_ipi_guideline_view.xml',
        # 'views/l10n_br_account_product_icms_relief_view.xml',
        # 'views/l10n_br_account_product_import_declaration_view.xml',
        # 'views/l10n_br_tax_icms_partition_view.xml',
        # 'views/account_payment_term_view.xml',
        # 'views/account_payment_term_view.xml',
        # 'views/account_invoice_view.xml',
        # 'wizards/l10n_br_account_invoice_costs_ratio_view.xml',
        # 'views/nfe/account_invoice_nfe_view.xml',
        # 'views/account_fiscal_position_view.xml',
        # 'views/res_country_view.xml',
        # 'views/account_payment_mode.xml',
        # 'wizards/l10n_br_account_nfe_export_invoice_view.xml',
        # 'wizards/l10n_br_account_nfe_export_view.xml',
        # 'wizards/l10n_br_account_document_status_sefaz_view.xml',
        # 'wizards/account_invoice_refund_view.xml',
        # 'report/account_invoice_report_view.xml',
    ],
    'demo': [
        'demo/partner_demo.xml',
        # 'demo/account_fiscal_position_rule_demo.xml',
        # 'demo/product_taxes.yml',
        # 'demo/account_invoice_demo.yml',
        # 'demo/account_invoice_demo.xml',
        # 'demo/account_nfe_demo.yml',
        # 'demo/account_nfe_demo.xml',
        # 'demo/account_nfe_supplier_demo.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    "external_dependencies": {"python": ["erpbrasil.assinatura"]},
}
