# Copyright (C) 2020 - Carlos R. Silveira - ATSti Soluções
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{  
    'name': 'Envio de MDF-e',
    'summary': """Permite o envio de MDF-e através das faturas do Odoo
    """,
    'description': 'Envio de MDF-e',
    'version': '12.0.1.0.0',
    'category': 'account',
    'author': 'ATSti',
    'license': 'AGPL-3',
    'website': 'http://www.atsti.com.br',
    'contributors': [
        'Carlos R. Silveira <crsilveira@gmail.com>',
    ],
    'depends': [
        'br_nfe',
    ],
    'external_dependencies': {
        'python': [
            'pytrustnfe', 'pytrustnfe.mdfe',
            'pytrustnfe.certificado', 'pytrustnfe.utils'
        ],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/invoice_eletronic.xml',
        'views/res_company.xml',
        'views/doc_referenciado.xml',
        'views/doc_veiculo.xml',
        'views/doc_seguro.xml',
        'views/doc_lacre.xml',
    ],
    'installable': True,
    'application': True,
}
