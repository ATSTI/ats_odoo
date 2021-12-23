# © 2021 Carlos R. Silveira, Manoel dos Santos, ATSti Solucoes
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo import tools


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # titular = fields.Boolean('Titular')  parent_id
    birthdate_n = fields.Date('Data de Nascimento')
    #'contracts_as_customer = fields.one2many('account.analytic.account','partner_id', 'Contratos cliente')
    sexo = fields.Selection([('F', 'Feminino'),('M', 'Masculino')], "Sexo")
    estado_civil = fields.Selection([
        ('1','CASADO(A)'),
        ('2','VIVUVO(A)'),
        ('3','DESQUITADO(A)'),
        ('4','DIVORCIADO(A)'),
        ('5','SOLTEIRO'),
        ('6','AMAZIADO'),
        ('7','OUTROS'),
        ('8','UNIÃO ESTAVEL')], "Estado Civil")
    mat_regime = fields.Selection([
        ('1','Comunhão parcial de bens'),
        ('2','Comunhão universal de bens'),
        ('3','Separação de bens'),
        ('4','Participação final nos aquestos')], "Regime")
    # grupo = fields.Char("Grupo", size=1)
    # inscricao = fields.Integer('Nº Inscrição') name contract
    naturalidade = fields.Char('Natural', size=100)
    # plano = fields.Selection([('7','7 FALECIMENTO'),
    #     ('M','MENSAL'),
    #     ('T','TRIMESTRAL'),
    #     ('P','PARTICULAR')], "Plano de Pgto")
    rg = fields.Char("RG" , size= 50)
    dtfalec = fields.Date('Data de Falecimento')
    dtacadastro = fields.Date('Data Cadastro')
    falecido = fields.Selection([('S','Sim'),('N','Não')], "Falecido")
    profissao = fields.Char('Profissão',size=100)
    parentesco = fields.Selection([('0','SOCIO'),
        ('1','ESPOSA'),
        ('2','ESPOSO'),
        ('3','SOGRA'),
        ('4','SOGRO'),
        ('5','MÃE'),
        ('6','PAI'),
        ('7','FILHO'),
        ('8','FILHA'),
        ('9','DEPENDENTE'),
        ('10','COMPANHEIRO(A)') ], "Grau de Parentesco")
    # cobra_dep = fields.Selection([('S','Sim'),
        # ('N','Não')], "Dep. Adicional")
    # status = fields.Selection([('A','Ativo'),
    #     ('I','Inativo'),
    #     ('O','Outros')], "Situação")
    # faixa = fields.Integer('Faixa')
    diapgto = fields.Integer('Dia Para Pgto')
    # id_cob = fields.Selection([('1','BOLETO BANCARIO'),
        # ('5','ESCRITORIO')], "Cobrador")
    #obs = fields.Text('obs')
    #'site_url = fields.char("Arquivo Morto", size=128)
    use_parent_address = fields.Boolean(string='Usar endereço do Socio')
        
    def _check_cnpj_cpf(self, cr, uid, ids):
        '''
        for partner in self.browse(cr, uid, ids):
            if not partner.cnpj_cpf:
                continue

            if partner.is_company:
                if not fiscal.validate_cnpj(partner.cnpj_cpf):
                    return False
            elif not fiscal.validate_cpf(partner.cnpj_cpf):
                    return False
        '''
        return True    
    
    
    
    """
    @api.model
    def create(self, vals):
        #import pudb;pu.db
        if not vals.get('parent_id'):		
            vals['titular'] = True
        cliente_id = super(ResPartner, self).create(vals)

        if not vals.get('parent_id'):
            #contato_id = self.copy(self._cr, self._uid)
            valor = {'parent_id': cliente_id.id, 'name': vals.get('name'), 'titular': False, 'parentesco': 'Socio'}
            #contato_id = self.env['res.partner'].sudo().create(valor)
            contato_id = super(ResPartner, self).create(valor)
            #vals['parente_id'] = cliente_id
            #contato = self.browse(contato_id)
            #self.write(vals)
        #return super(ProjectTaskTi, self).create(vals)
        return cliente_id    
    """
    
    
#ResPartner()

"""
class partner_aniversario(osv.osv):
    _name = "partner_aniversario"
    _description = "tree map"
    _auto = False
    _columns = {
        "partner": fields.char("Cliente", size=128),
        "partner_id": fields.many2one("res.partner", u"Parceiro", store=False),
        "familiar":fields.char("Familiar", size=128),
        "parentesco": fields.char("Parentesco", size=30),
        'niver': fields.date('Date de nascimento'),
        "email": fields.char("Email", size=128),
        "phone": fields.char("Fone", size=30),
        'dia_nasc': fields.integer('Dia nascimento'),
        'mes_nasc': fields.integer('Mes nascimento'),
        'ordem': fields.integer('Ordem'),
       }

    _order = "partner, ordem"
"""

"""
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'partner_aniversario')
        cr.execute(\""" create or replace view partner_aniversario AS (
                  (select distinct rp.name partner, rp.id, rp.birthdate_n, 'Titular'
                     familiar, 'Titular' parentesco 
                     ,extract(day from rp.birthdate_n) as dia_nasc
                     ,extract(month from rp.birthdate_n) as mes_nasc
                     ,rp.birthdate_n niver, rp.email, rp.phone, 0 ordem
                     ,rp.id partner_id
                   from res_partner rp
                  where rp.titular = true
                    and rp.customer = true
                 )
  
                 UNION

                (select distinct rpt.name partner, rp.id, rp.birthdate_n,
                    rp.name familiar, pc.name parentesco
                    ,extract(day from rp.birthdate_n) as dia_nasc
                    ,extract(month from rp.birthdate_n) as mes_nasc
                    ,rp.birthdate_n niver, rp.email, rp.phone, 1 ordem
                    ,rpt.id partner_id
                  from res_partner rp, res_partner rpt, res_partner_res_partner_category_rel pcr, res_partner_category pc
                 where rpt.id = rp.parent_id 
                   and rp.id = pcr.partner_id 
                   and pcr.category_id = pc.id 
                   -- and rp.customer = true 
                   -- and rp.titular = false
                   and rp.parent_id is not null 
                )   
                order by partner, ordem 
                )
        \""")
"""
