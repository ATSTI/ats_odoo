# © 2021 Carlos R. Silveira, Manoel dos Santos, ATSti Solucoes
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Funerarias',
    'version': '1.0',
    'category': 'Others',
    'sequence': 2,
    'summary': 'ATSti Sistemas Funerarios',
    'description': """
        Sistema de Controle Funerario
   """,
    'author': 'ATS Soluções',
    'website': '',
    'depends': ['account', 'l10n_br_base'],
    'data': [
        'security/obito_groups.xml',
        'security/ir.model.access.csv',
        'security/inherited_ir_model_access_data_obito_grupo.xml',
        'views/obito_view.xml',
        'views/res_partner_views.xml',
        #'data/obito.xml',
        'views/obito_grupo_views.xml'
    ],
    'installable': True,
    'application': False,
}

