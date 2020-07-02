# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PaymentAccountMoveLine(models.TransientModel):
    _inherit = "payment.account.move.line"

    juros = fields.Monetary(
        string='Juros', readonly=True)
    multa = fields.Monetary(
        string='Multa', readonly=True)
    #data_vencimento = fields.Date(
    #    string='Data Vencimento', readonly=True,
    #    related='move_line_id.date_maturity')

    #compute='_compute_juros_multa', 
    @api.model
    def default_get(self, fields):
        import pudb;pu.db
        rec = super(PaymentAccountMoveLine, self).default_get(fields)
        move_line_id = rec.get('move_line_id', False)
        company = move_line_id.company_id
        current_date = fields.Date.today()
        quantidade_dias = abs(
            (current_date - move_line_id.date_maturity).days) - company.tolerance_interval
            #if self.multa:
        multa = move_line_id.amount * (company.multa/100)
        amount = company.currency_id.round(
            ((company.rate/100) * quantidade_dias * move_line_id.amount)+multa)
        rec.update({
            'multa': multa,
            'juros': juros,
        })

        return rec
        
        
    """
    @api.one
    @api.depends('move_line_ids.debit',
                 'move_line_ids.date_maturity',
                 'move_line_ids.company_id', 'move_line_ids')
    def _compute_juros_multa(self):
        if not self.reconciled:
            import pudb;pu.db
            amount = 0.0
            company = move_line_ids.company_id
            current_date = fields.Date.today()
            quantidade_dias = abs(
                (current_date - move_line_ids.date_maturity).days) - company.tolerance_interval
            #if self.multa:
            multa = move_line_ids.debit * (company.multa/100)
            amount = company.currency_id.round(
                ((company.rate/100) * quantidade_dias * amount)+multa)
            
            
            #self.e_cheque = False
            #if self.journal_id.code == 'chk':
            #    self.e_cheque  = True
    """
