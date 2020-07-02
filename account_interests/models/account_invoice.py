# © 2016 Alessandro Fernandes Martini, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.one
    @api.depends('amount_residual', 'date_due', 'state')
    def _calcula_juros_multa(self):
        import pudb;pu.db
        if self.product_document_id:
            return
        if self.state != 'open':
            return
        current_date = fields.Date.today()
        if self.date_due >= current_date:
            return
        rec = self.env['res_company'].search([('next_date', '<=', current_date)])
        interests_date = rec.next_date
        if interests_date > current_date:
            return

        rule_type = rec.rule_type
        interval = rec.interval
        tolerance_interval = rec.tolerance_interval
        # next_date = fields.Date.from_string(interests_date)
        if rule_type == 'daily':
            next_delta = relativedelta(days=+interval)
            tolerance_delta = relativedelta(days=+tolerance_interval)
        elif rule_type == 'weekly':
            next_delta = relativedelta(weeks=+interval)
            tolerance_delta = relativedelta(weeks=+tolerance_interval)
        elif rule_type == 'monthly':
            next_delta = relativedelta(months=+interval)
            tolerance_delta = relativedelta(months=+tolerance_interval)
        else:
            next_delta = relativedelta(years=+interval)
            tolerance_delta = relativedelta(years=+tolerance_interval)
        interests_date_date = fields.Date.from_string(interests_date)
        # buscamos solo facturas que vencieron
        # antes de hoy menos un periodo
        # TODO ver si queremos que tambien se calcule interes proporcional
        # para lo que vencio en este ultimo periodo
        to_date = fields.Date.to_string(
            interests_date_date - tolerance_delta)

        
        line.action_invoice_cancel()
        line.action_invoice_draft()        
        
        # seteamos proxima corrida en hoy mas un periodo
        rec.next_date = fields.Date.to_string(
            interests_date_date + next_delta)

        lang_code = self.env.context.get('lang', self.env.user.lang)
        lang = self.env['res.lang']._lang_get(lang_code)
        date_format = lang.date_format
        to_date_format = fields.Date.from_string(
            to_date).strftime(date_format)

        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id)], limit=1)
        
        # TODO se usa boleto, nao da pra cancelar a fatura
        #import pudb;pu.db
        #('boleto', '=', False),
        
        invoice_domain = [
            ('account_id', 'in', self.receivable_account_ids.ids),
            ('state', '=', 'open'),
            ('date_due', '<', to_date),
            ('product_document_id', '=', False),
        ]

        # Check if a filter is set
        #if self.domain:
        #    account_domain += safe_eval(self.domain)

        invoice = self.env['account.invoice']
        invoice_ids = invoice.search(invoice_domain)
        #    fields=['id', 'amount_residual', 'partner_id', 'account_id'],
        #    groupby=['partner_id'],
        #)
        #fields=['id', 'amount_residual', 'partner_id', 'account_id'],  estava antes do groupby acima
        #self = self.with_context(mail_notrack=True, prefetch_fields=False)

        total_items = len(invoice_ids)
        _logger.info('%s interest invoices will be generated', total_items)
        import pudb;pu.db
        idx = 0
        for line in invoice_ids:

            debt = line.residual

            if not debt or debt <= 0.0:
                continue

            _logger.info(
                'Creating Interest Invoice (%s of %s) with values:\n%s',
                idx + 1, total_items, line)
            idx += 1
            partner_id = line.partner_id.id
            # PRECISO DISTO ??
            #partner = self.env['res.partner'].browse(partner_id)
            
            
            #invoice_vals = self._prepare_interest_invoice(
            #    partner, debt, to_date, journal)
            
            # cancelo a FATURA : 
            line.action_invoice_cancel()
            line.action_invoice_draft()
            
            # we send document type for compatibility with argentinian
            # invoices
            #invoice = self.env['account.invoice'].with_context(
            #    internal_type='debit_note').create(invoice_vals)

            line.invoice_line_ids.create(#
                self._prepare_interest_invoice_line(
                    line, debt, to_date_format))

            # update amounts for new invoice
            line.compute_taxes()
            if self.automatic_validation:
                try:
                    invoice.action_invoice_open()
                except Exception as e:
                    _logger.error(
                        "Something went wrong "
                        "creating interests invoice: {}".format(e))

        
        
    juros_multa = fields.Monetary(string='Juros/Multa',
        store=True, readonly=True, compute='_calcula_juros_multa')

