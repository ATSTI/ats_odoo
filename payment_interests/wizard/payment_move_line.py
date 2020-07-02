# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date

class AccountPayment(models.Model):
    _inherit = "account.payment"

    juros = fields.Monetary(
        string='Juros', readonly=True)
    multa = fields.Monetary(
        string='Multa', readonly=True)
    valor_original = fields.Monetary(
        string='Vlr. Original', readonly=True)
    incluir_juros = fields.Boolean(string="Incluir Juros/Multa")
 
    @api.model
    def default_get(self, fields):
        if 'move_line_id' in fields:
            rec = super(AccountPayment, self).default_get(fields)
        else:
            return super(AccountPayment, self).default_get(fields)
        move_line_id = rec.get('move_line_id', False)
        move_line = self.env['account.move.line'].browse(move_line_id)
        current_date = date.today()
        cpn = self.env['res.company.interest'].browse(move_line.company_id.id)
        quantidade_dias = abs((current_date - move_line.date_maturity).days)
        if quantidade_dias < cpn.tolerance_interval:
            return rec
        quantidade_dias = quantidade_dias - cpn.tolerance_interval
        multa = move_line.debit * (cpn.multa/100)
        juros = cpn.company_id.currency_id.round(
            (cpn.rate/100) * quantidade_dias * move_line.debit)
        rec.update({
            'multa': multa,
            'juros': juros,
            'valor_original': move_line.debit,
        })

        return rec

    @api.onchange('incluir_juros')
    def _onchange_incluir_juros(self):
        if self.incluir_juros:
            self.amount = self.amount + self.juros + self.multa
        if not self.incluir_juros and self.amount > self.valor_original:
            self.amount = self.valor_original
