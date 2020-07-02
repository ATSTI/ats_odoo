# © 2016 Alessandro Fernandes Martini, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

STATE = {'edit': [('readonly', False)]}


class InvoiceEletronic(models.Model):
    _inherit = 'invoice.eletronic'
    
    """
    # LOTE
    lote_ids = fields.One2many(
        'nfe.lote', 'lote_id',
        string=u"Cartas de Correção", readonly=True, states=STATE)
    # uso no sped
    """

    @api.multi
    def _prepare_eletronic_invoice_item(self, item, invoice):
        import pudb;pu.db
        res = super(InvoiceEletronic, self)._prepare_eletronic_invoice_item(
            item, invoice)
        # se existir mais de um lote informado para o mesmo ite, 
        # então criar mais linhas na nfe
        lotes = []
        for linha in item.account_invoice_line_id.sale_line_ids:
            lote_ids = self.env['stock.move'].search([
                ('sale_line_id', '=', linha.id)])
            for lt in lote_ids.move_line_ids:
                lotes.append({
                    'nLote': lt.name,
                    'qLote': 1,
                    'dFab' : lt.fabricate_date,
                    'dVal' : lt.expiry_date,
                })
            if lotes:
                res['prod'].update({'rastro': lotes})
        return res
                
"""
class NfeLote(models.Model):
    _name = 'nfe.lote'
    _description = "Lote dos Produtos(Rastreabilidade)"
    
    lote_id = fields.Many2one(
        'invoice.eletronic', string=u"Documento Eletrônico")
    lote = fields.Char(string="Lote")
    data_vencimento = fields.Date(string="Data Vencimento")
    data_fabricacao = fields.Date(string="Data Fabricação")
"""
