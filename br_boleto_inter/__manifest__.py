
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Pagamentos via Boleto Bancário',
    'summary': """Dependente da localizacão da TrustCode""",
    'description': """Permite integração com a API do Banco INTER""",
    'version': '12.0.1.0.0',
    'category': 'account',
    'author': 'ATSTi',
    'license': 'AGPL-3',
    'website': 'http://www.atsti.com.br',
    'depends': [
        'br_account_payment', 'br_data_account_product','br_boleto',
    ],
    'data': [
        'views/account_journal.xml',
        'views/account_move_line.xml',
    ],
    'installable': True,
    'application': True,
}
