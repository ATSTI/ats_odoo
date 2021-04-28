# © 2016 Alessandro Fernandes Martini, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ambiente_mdfe = fields.Selection(
        [("1", u"Produção"), ("2", u"Homologação")],
        string="Ambiente MDFe",
        default="2",
    )
    cabecalho_danfe_mdfe = fields.Selection(
        [
            ("vertical", "Modelo Vertical"),
            ("horizontal", "Modelo Horizontal"),
        ],
        string=u"Cabeçalho Danfe MDFe", default="vertical",)
    tipo_emitente_mdfe = fields.Selection(
        [("1", u"Transportadora"), ("2", u"Carga Própria")],
        string="Emitente MDFe", default="2",)
    serie_mdfe = fields.Many2one(
        'br_account.document.serie', string=u'Série MDFe',)
    tipo_transportador = fields.Selection(
        [('1', 'ETC'), ('2', 'TAC'), ('3', 'CTC')],
        string='Tipo do transportador'
    )
