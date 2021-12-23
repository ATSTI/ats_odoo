from odoo import _, api, fields, models
from odoo.exceptions import UserError



class ContractContract(models.Model):
    _inherit = "contract.contract"

    def _altera_nome_grupo(self, grupo):
        insc = grupo.inscricao+1
        name = ''
        if grupo.faixa:
            if insc > grupo.insc_ini and insc < grupo.insc_fim:
                name = '{}-{}'.format(grupo.codigo , insc)
            else:
                raise UserError(_("Grupo já completo"))
        else:
            name = '{}-{}'.format(grupo.codigo , insc)
        return insc, name

    @api.onchange("grupo")
    def on_change_grupo(self):
        self.inscricao, self.name = self._altera_nome_grupo(self.grupo)

    # def _prepare_invoice(self, date_invoice, journal=None):
    #     invoice_vals, move_form = super()._prepare_invoice(
    #         date_invoice=date_invoice, journal=journal
    #     )
    #     if self.payment_mode_id:
    #         invoice_vals["payment_mode_id"] = self.payment_mode_id.id
    #     return invoice_vals, move_form
    plano = fields.Selection([('7','7 FALECIMENTO'),
        ('M','MENSAL'),
        ('T','TRIMESTRAL'),
        ('P','PARTICULAR')], "Plano de Pgto")
    cobra_dep = fields.Selection([('S','Sim'),
        ('N','Não')], "Dep. Adicional")
    faixa = fields.Integer('Faixa')
    id_cob = fields.Selection([('1','BOLETO BANCARIO'),
        ('5','ESCRITORIO')], "Cobrador")
    grupo = fields.Many2one(
        comodel_name="obito.grupo",
        string="Grupo")
    inscricao = fields.Integer('Nº Inscrição') 

    @api.model
    def create(self, vals):
        if not 'name' in vals:
            vals['name'] = '/'
        new_record = super().create(vals)
        if not 'inscricao' in vals or not 'name' in vals:
            insc, name = self._altera_nome_grupo(new_record.grupo)
            new_record.inscricao = insc
            new_record.name = name
        
        new_record.grupo.write({'inscricao': new_record.inscricao})
        return new_record