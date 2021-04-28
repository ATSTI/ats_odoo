# © 2016 Danimar Ribeiro <danimaribeiro@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class DocLacre(models.Model):
    _name = 'doc.lacre'
    _description = "MDF-e Lacres"

    name = fields.Char(string="Lacre")


class DocSeguro(models.Model):
    _name = 'doc.seguro'
    _description = "Seguro"

    name = fields.Char(string='Seguradora')
    seguradora_cnpj = fields.Char(string='Seguradora CNPJ')
    responsavel_seguro = fields.Selection([
        ('1', 'Emitente do MDF-e'),
        ('2', 'Responsável - contratante')],
        string='Responsável seguro',
    )
    responsavel_cnpj_cpf = fields.Char(string='CNPJ/CPF',
        help='Obrigatório se Responsável Seguro = 2')
    numero_apolice = fields.Char(string='Numero da apólice')
    numero_averbacao = fields.Char(string='Número da Averbação')


class DocVeiculo(models.Model):
    _name = 'doc.veiculo'
    _description = 'veiculo MDFe'

    name = fields.Char(string='Placa')
    renavam = fields.Char(string='Renavam')
    rntrc = fields.Char(string='RNTRC')
    ciot = fields.Char(string='Ciot', help='Código Identificador da \
        Operação de Transporte. Também Conhecido como conta frete.')
    uf = fields.Many2one(comodel_name='res.country.state', string='Estado')
    veiculo_tipo = fields.Selection(
        [(0, u'Veiculo'), (1, u'Reboque')],
        string='Veículo ou Reboque', default=0)
    tipo_rodado = fields.Selection(
        [('01', 'Truck'),
        ('02', 'Toco'),
        ('03', 'Cavalo Mecânico'),
        ('04', 'VAN'),
        ('05', 'Utilitário'),
        ('06', 'Outros')],
        string='Rodado', required=True,
    )
    tipo_carroceria = fields.Selection(
        [('00', 'Não aplicável'),
        ('01', 'Aberta'),
        ('02', 'Fechada/Baú'),
        ('03', 'Granelera'),
        ('04', 'Porta Container'),
        ('05', 'Sider')],
        string='Tipo de carroceria', required=True,
    )
    tara_kg = fields.Float(
        string='Tara (kg)'
    )
    capacidade_kg = fields.Float(
        string='Capacidade (kg)',
    )
    capacidade_m3 = fields.Float(
        string='Capacidade (m³)'
    )
    proprio = fields.Boolean(string='Veículo Próprio ?', default=False)
    proprietario =  fields.Char(string='Proprietário')    
    proprietario_rntrc = fields.Char(string='Proprietario RNTRC')
    proprietario_cnpj_cpf = fields.Char(string='CNPJ/CPF')
    proprietario_ie = fields.Char(string='Inscrição Estadual')
    proprietario_uf = fields.Many2one("res.country.state", string='UF', 
        ondelete='restrict')
    proprietario_rntrc = fields.Char(string='Proprietario RNTRC',
        help=u"Registro Nacional de Transportador de Carga")
    tipo_proprietario = fields.Selection(
        [('0', 'TAC – Agregado'),
        ('1', 'TAC Independente'),
        ('2', 'Outros')],
        string='Tipo Proprietário',
    )

class DocVeiculoReboque(models.Model):
    _name = 'doc.veiculo.reboque'
    _description = 'Veiculo/Reboque'

    invoice_eletronic_id = fields.Many2one('invoice.eletronic', string="MDFe")
    veiculo_id = fields.Many2one(
        'doc.veiculo', string='Veiculo/Reboque')
    veiculo_tipo = fields.Selection(
        related='veiculo_id.veiculo_tipo',
        string='Veículo ou Reboque', readonly=True)
    veiculo_renavam = fields.Char(string='Renavam', 
        related='veiculo_id.renavam',
        readonly=True)
    veiculo_uf = fields.Many2one(comodel_name='res.country.state', 
        string='Estado', related='veiculo_id.uf',readonly=True)
    veiculo_rntrc = fields.Char(string='RNTRC', related='veiculo_id.rntrc',
        readonly=True)


class DocReferenciado(models.Model):
    _name = 'doc.referenciado'
    _description = 'Documento MDF-E Carga Item'

    @api.onchange('documento_id')
    def _onchange_documento_id(self):
        if self.documento_id:
            self.documento_modelo = self.documento_id.model
            self.documento_chave = self.documento_id.chave_nfe
            self.documento_uf = self.documento_id.partner_id.state_id.id
            self.documento_municipio = self.documento_id.partner_id.city_id.id
            self.valor = self.documento_id.valor_final
            for vl in self.documento_id.volume_ids:
                #self.peso_liquido += vl.peso_liquido
                self.peso_bruto += vl.peso_bruto
   
    invoice_eletronic_id = fields.Many2one('invoice.eletronic', string="MDFe")
    documento_id = fields.Many2one(
        'invoice.eletronic', string='Documento próprio')
    documento_modelo = fields.Selection(
        [('55', u'NF-e - 55'),
         ('57', u'CT-e - 57'),
         ('58', u'MDF-e - 58')],
        string='Documento',
    )
    documento_chave = fields.Char(
        string='Chave',
        size=44,
        copy=False,
    )
    documento_uf = fields.Many2one("res.country.state", string='UF', 
        ondelete='restrict')
    documento_municipio = fields.Many2one(                                                                                                                            
        'res.state.city', u'Municipio',                                                                                                                        
         domain="[('state_id','=',documento_uf)]")
    peso_bruto = fields.Float(string='Peso Bruto', default=0.0)
    #peso_liquido = fields.Float(string='Peso Liquido', default=0.0)
    valor = fields.Float(string='Valor Total', default=0.0)    
