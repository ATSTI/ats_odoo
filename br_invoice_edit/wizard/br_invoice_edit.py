# -*- coding: utf-8 -*-
from odoo import api, fields, models
import base64
import re
from datetime import datetime
from datetime import timedelta
from odoo.exceptions import UserError


class BrInvoiceEdit(models.TransientModel):
    _name='br.invoice.edit'

    company_id = fields.Many2one('res.company', string='Company', change_default=True,
        required=True, readonly=True, 
        default=lambda self: self.env['res.company']._company_default_get('account.invoice'))
    product_serie_id = fields.Many2one(
        'br_account.document.serie', string=u'Série produtos',
        domain="[('fiscal_document_id', '=', product_document_id),\
        ('company_id','=',company_id)]", readonly=True)
    product_document_id = fields.Many2one(
        'br_account.fiscal.document', string='Documento produtos'
        )
    service_serie_id = fields.Many2one(
        'br_account.document.serie', string=u'Série serviços',
        domain="[('fiscal_document_id', '=', service_document_id),\
        ('company_id','=',company_id)]")
    service_document_id = fields.Many2one(
        'br_account.fiscal.document', string='Documento serviços')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')


    def criar_documento(self):
        fatura = self._context.get('active_id')
        invoice = self.env['account.invoice'].browse([fatura])
        invoice.write({'invoice_edit': True})
        invoice.action_cancel()
