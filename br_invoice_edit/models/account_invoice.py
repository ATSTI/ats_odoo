# Copyright 2016 Acsone SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    invoice_edit = fields.Boolean(
        string='Editada pós faturamento',
        readonly=True,
    )

    @api.multi
    def action_cancel(self):
        if not self.invoice_edit:
            return super(AccountInvoice, self).action_cancel()
        else:
            self.write({'state': 'cancel', 'move_id': False})
        return True

    @api.multi
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        if not self.invoice_edit:
            return super(AccountInvoice, self).action_invoice_open()
        else:
            return self.invoice_validate()

    @api.multi
    def action_move_create(self):
        if not self.invoice_edit:
            super(AccountInvoice, self).action_move_create()
        else:
            return True

    @api.multi
    def invoice_validate(self):
        for invoice in self:
            if invoice.partner_id not in invoice.message_partner_ids:
                invoice.message_subscribe([invoice.partner_id.id])

            # Auto-compute reference, if not already existing and if configured on company
            if not invoice.reference and invoice.type == 'out_invoice':
                invoice.reference = invoice._get_computed_reference()

            # DO NOT FORWARD-PORT.
            # The reference is copied after the move creation because we need the move to get the invoice number but
            # we need the invoice number to get the reference.
            if not self.invoice_edit:
                invoice.move_id.ref = invoice.reference
            else:
                # a move ja existe entao vou buscar
                move = self.env['account.move'].search([
                    ('ref','=',invoice.reference)
                ], order='id', limit=1)
                if move:
                    invoice.update({
                        'number': move.name,
                        'move_id': move.id
                    })
        self._check_duplicate_supplier_reference()

        self.update({'state': 'open'})
        
        for item in self:
            if item.product_document_id.electronic:
                if item.company_id.l10n_br_nfse_conjugada:
                    inv_lines = item.invoice_line_ids
                else:
                    inv_lines = item.invoice_line_ids.filtered(
                        lambda x: x.product_id.fiscal_type == 'product')
                if inv_lines:
                    edoc_vals = self._prepare_edoc_vals(
                        item, inv_lines, item.product_serie_id)
                    eletronic = self.env['invoice.eletronic'].create(edoc_vals)
                    eletronic.validate_invoice()
                    eletronic.action_post_validate()

            if item.service_document_id.nfse_eletronic and \
               not item.company_id.l10n_br_nfse_conjugada:
                inv_lines = item.invoice_line_ids.filtered(
                    lambda x: x.product_id.fiscal_type == 'service')
                if inv_lines:
                    edoc_vals = self._prepare_edoc_vals(
                        item, inv_lines, item.service_serie_id)
                    
                    eletronic = self.env['invoice.eletronic'].create(edoc_vals)
                    eletronic.validate_invoice()
                    eletronic.action_post_validate()
        