# © 2021 Carlos R. Silveira <crsilveira@gmail.com>, ATSTi
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models, _



class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.onchange('fiscal_position_id')
    def _onchange_br_account_fiscal_position_id(self):
        res = super(AccountInvoice, self)._onchange_br_account_fiscal_position_id()
        # atualiza tributos dos produtos
        if self.fiscal_position_id:
            for linha in self.invoice_line_ids:
                fpos = self.fiscal_position_id
                if fpos:
                    vals = fpos.map_tax_extra_values(
                    self.company_id, linha.product_id, self.partner_id)

                    for key, value in vals.items():
                        if value and key in linha._fields:
                            if isinstance(value, (int, bool, float, complex, str)):
                                linha.write({key: value})
                            else: 
                                linha.write({key: value.id})
                    self.tax_line_move_line_get()
        return res

