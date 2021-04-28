# © 2016 Danimar Ribeiro <danimaribeiro@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
import io
import base64
import logging
import hashlib
from lxml import etree
from datetime import datetime
from pytz import timezone
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)
#import pudb;pu.db
#try:
from pytrustnfe.mdfe import autorizar_mdfe
from pytrustnfe.mdfe import retorno_autorizar_mdfe
from pytrustnfe.mdfe import recepcao_evento_cancelamento
from pytrustnfe.mdfe import xml_consulta_situacao_mdfe
from pytrustnfe.mdfe import xml_render_mdfe
from pytrustnfe.mdfe import consulta_situacao_mdfe
from pytrustnfe.certificado import Certificado
from pytrustnfe.utils import ChaveMDFe,  gerar_mdfeproc, \
    gerar_chave_mdfe
#from pytrustnfe.mdfe.danfe import danfe
from pytrustnfe.xml.validate import valida_mdfe
from pytrustnfe.urls import url_qrcode
#except ImportError:
#   _logger.error('Cannot import pytrustnfe', exc_info=True)

STATE = {'edit': [('readonly', False)]}


class InvoiceEletronic(models.Model):
    _inherit = 'invoice.eletronic'

    @api.multi
    @api.depends('chave_nfe')
    def _compute_format_danfe_key(self):
        for item in self:
            item.chave_nfe_danfe = re.sub("(.{4})", "\\1.",
                                          item.chave_nfe, 10, re.DOTALL)

    @api.multi
    def generate_correction_letter(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "wizard.carta.correcao.eletronica",
            "views": [[False, "form"]],
            "name": _("Carta de Correção"),
            "target": "new",
            "context": {'default_eletronic_doc_id': self.id},
        }
        
    def _compute_dados(self):
        # TODO
        return True

    model = fields.Selection(selection_add=[('58', u'58 - MDFe')])
    tipo_emitente_mdfe = fields.Selection(
        string='Tipo de emitente', related='company_id.tipo_emitente_mdfe',
        readonly=True)
    ambiente_mdfe = fields.Selection(
        string='Ambiente MDFe', related='company_id.ambiente_mdfe',
        readonly=True)
    tipo_transportador = fields.Selection(
        string='Transportador', related='company_id.tipo_transportador',
        readonly=True)
    modal = fields.Selection(
        [('1', 'Rodoviário'), ('2', 'Aéreo'), ('3', 'Aquaviário'),
        ('4', 'Ferroviário')],
        string='Modal'
    )  
    carregamento_municipio_ids = fields.Many2many(
        'res.state.city',  string='Municípios carregamento',
        help='Máximo 60')
    descarregamento_estado_ids = fields.Many2many(
        'res.country.state', string = 'UF Descarregamento',
        help='Máximo 25')
    percurso_estado_ids = fields.Many2many(
        'res.country.state', string = 'UFs de percurso',
        help='Máximo 25')
    tipo_unid_transporte = fields.Selection(
        [('1', 'Rodoviário Tração'),
        ('2', 'Rodoviário Reboque'),
        ('3', 'Navio'),
        ('4', 'Balsa'),
        ('5', 'Aeronave'),
        ('6', 'Vagão'),
        ('7', 'Outros')],
        string='Tipo unidade transportador')
    id_unid_transp = fields.Char(
        string='Identificação da Unidade',
        help='Exemplo: Placa, N. Container')
    tipo_unid_carga = fields.Selection(
        [('1', 'Container'),
        ('2', 'ULD'),
        ('3', 'Pallet'),
        ('4', 'Outros')],
        string='Tipo da Unidade de Carga')
    id_unid_carga = fields.Char(
        string='Identificação unidade Carga',
        help='Exemplo: Número do Container')
    seguro_ids = fields.Many2one('doc.seguro', string='Seguro')
    qtde_cte = fields.Integer(
        string='Quantidade CTe', 
        compute=_compute_dados)
    qtde_nfe = fields.Integer(
        string='Quantidade NFe', 
        compute=_compute_dados)
    qtde_mdfe = fields.Integer(
        string='Quantidade MDFe', 
        compute=_compute_dados)
    peso_bruto = fields.Float(string='Peso Bruto', default=0.0)
    unidade_carga = fields.Selection(
        [('1', 'KG'), ('2', 'TON')],
        string='Unidade da Carga',
        help='Código da unidade de medida do Peso Bruto da Carga / \
             Mercadorias transportadas.')
    # TODO infRespTec usando do cadastro Empresa
    veiculo_ids = fields.One2many('doc.veiculo.reboque', 
        'invoice_eletronic_id', string=u"Veiculo/Reboque")
    lacre_ids = fields.Many2one('doc.lacre', string='Lacre')
    condutor_ids = fields.Many2one(
        'res.partner', string=u"Condultor(es)")
    document_related_ids = fields.One2many(
        'doc.referenciado', 'invoice_eletronic_id',
        string='Documentos relacionados: NFe, CTe, MDFe')

    @api.model
    def create(self, vals):
        #import pudb;pu.db
        if not 'company_id' in vals:
            company = self.env['res.company']._company_default_get('account.invoice')
            vals['company_id'] = company.id
        else:
            company = vals['company_id']
        #cpn = self.env['res.company'].browse([company])
        res = super(InvoiceEletronic, self).create(vals)
        if res.model == '58' and not res.company_id.serie_mdfe:
            raise UserError(
                _('Nenhuma SÉRIE cadastrada para MDFe, no cadastro da  \
                  Empresa.'))
        #import pudb;pu.db
        if res.model == '58' and res.code == '0':
            ultimo_num = self.env['invoice.eletronic'].search([
            ('serie', '=', res.company_id.serie_mdfe.id),
            ('model', '=', '58')],
            order='numero desc', limit=1).numero + 1
            mdfe = {
                'code': ultimo_num,
                'numero': ultimo_num,
                'serie': res.company_id.serie_mdfe.id,
                'serie_documento': res.company_id.serie_mdfe.code,
                'name': ultimo_num,
                'ambiente_mdfe': res.company_id.ambiente_mdfe,
            }
            res.write(mdfe)
        return res

    @api.multi
    def copy(self, default=None):
        res = super(InvoiceEletronic, self).copy()
        return res

    @api.multi
    def _prepare_eletronic_docs_values(self, doc_related):
        infDoc = []
        ListaDoc = []
        infMunDescarga = []
        infUnidCarga = []
        infUnidTransp = []
        #import pudb;pu.db
        if self.tipo_unid_carga:
            infUnidCarga.append({
                    'tpUnidCarga' : self.tipo_unid_carga,
                    'idUnidCarga' : self.id_unid_carga,
                    'qtdRat' : '1.00',            
            })
            infUnidTransp.append({
                'tpUnidTransp' : self.tipo_unid_transporte,
                'idUnidTransp' :  self.id_unid_transp,
                'infUnidCarga' : infUnidCarga,
                'qtdRat': '1.00',
            })
        for mun in doc_related:
            municipio = mun.documento_municipio.ibge_code
            if not mun.documento_municipio.ibge_code in ListaDoc:
                ListaDoc.append(mun.documento_municipio.ibge_code)
            for doc in self.document_related_ids:
                if municipio == doc.documento_municipio.ibge_code:            
                    if doc.documento_modelo == '55':
                        #infNFe = {'chNFe': doc.documento_chave}
                        #MunDescarga['infNFe'] = {'chNFe' : doc.documento_chave
                        infDoc.append({
                            'chNFe': doc.documento_chave,
                            'SegCodBarras': '',
                            'indReentrega': '',
                            'infUnidTransp': infUnidTransp,
                        })
                        """
                           'refNF': {
                                'cUF': doc.state_id.ibge_code,
                                'AAMM': data.strftime("%y%m"),
                                'CNPJ': re.sub('[^0-9]', '', doc.cnpj_cpf),
                                'mod': doc.fiscal_document_id.code,
                                'serie': doc.serie,
                                'nNF': doc.internal_number,
                            }
                        })
                        """
                    elif doc.documento_modelo == '57':
                        documentos.append({
                            'refCTe': doc.access_key
                        })
                    elif doc.document_type == 'nfrural':
                        cnpj_cpf = re.sub('[^0-9]', '', doc.cnpj_cpf)
                        documentos.append({
                              'refNFP': {
                              'cUF': doc.state_id.ibge_code,
                              'AAMM': data.strftime("%y%m"),
                              'CNPJ': cnpj_cpf if len(cnpj_cpf) == 14 else '',
                              'CPF': cnpj_cpf if len(cnpj_cpf) == 11 else '',
                              'IE': doc.inscr_est,
                              'mod': doc.fiscal_document_id.code,
                              'serie': doc.serie,
                              'nNF': doc.internal_number,
                              }
                        })
                    elif doc.document_type == 'cf':
                        documentos.append({
                            'refECF': {
                                'mod': doc.fiscal_document_id.code,
                                'nECF': doc.serie,
                                'nCOO': doc.internal_number,
                            }
                        })
                    #infMunDescarga.append({'infNfe': infDoc,})
                #else:
                #    if infDoc:
                #        infMunDescarga.append({'infNfe': infDoc,})
            #import pudb;pu.db
            #MunDescarga['infNFe'] = infDoc
            #    'infNFe': infDoc[0],
            cod_ibge = '%s%s' % (
                        mun.documento_municipio.state_id.ibge_code,
                        mun.documento_municipio.ibge_code)

            MunDescarga = {
                    'cMunDescarga':  cod_ibge,
                    'xMunDescarga': mun.documento_municipio.name,
                    'infNFe': infDoc
            }
            return {'municipios': [MunDescarga]}
        
    @api.multi
    def _prepare_eletronic_invoice_values(self):
        res = super(InvoiceEletronic, self)._prepare_eletronic_invoice_values()
        if self.model not in ('58'):
            return res          
        tz = timezone(self.env.user.tz)
        dt_emissao = datetime.now(tz).replace(microsecond=0).isoformat()
        dt_saida = fields.Datetime.from_string(self.data_entrada_saida)
        if dt_saida:
            dt_saida = tz.localize(dt_saida).replace(microsecond=0).isoformat()
        else:
            dt_saida = dt_emissao

        ide = {
            'cUF': self.company_id.state_id.ibge_code,
            'cMDF': "%08d" % self.id,
            'tpEmit': '2',
            'mod': self.model,
            'serie': self.serie.code,
            'nMDF': self.numero,
            'modal': '1',
            'dhEmi': dt_emissao,
            'dhSaiEnt': dt_saida,
            'tpNF': '0' if self.tipo_operacao == 'entrada' else '1',
            'idDest': self.ind_dest or 1,
            'cMunFG': "%s%s" % (self.company_id.state_id.ibge_code,
                                self.company_id.city_id.ibge_code),
            # Formato de Impressão do DANFE - 1 - Danfe Retrato, 4 - Danfe NFCe
            'tpImp': '1' if self.model == '55' else '4',
            'tpEmis': int(self.tipo_emissao),
            'tpAmb': int(self.ambiente_mdfe),
            'finNFe': self.finalidade_emissao,
            'procEmi': 0,
            'verProc': 'Odoo 12 - Trustcode',
        }
        #import pudb;pu.db
        for mun in self.carregamento_municipio_ids:
            ide['UFIni'] = mun.state_id.code
            MunCarrega = {
                    'cMunCarrega': '%s%s' %(mun.state_id.ibge_code, mun.ibge_code),
                    'xMunCarrega': mun.name,}
        ide['infMunCarrega'] = [MunCarrega]

        for estado in self.percurso_estado_ids:
            Percurso = {
                    'UFPer':estado.code,}
        ide['infPercurso'] = [Percurso]
        
        # emit
        emit = {
            'tipo': self.company_id.partner_id.company_type,
            'cnpj_cpf': re.sub('[^0-9]', '', self.company_id.cnpj_cpf),
            'IE': re.sub('[^0-9]', '', self.company_id.inscr_est),
            'xNome': self.company_id.legal_name,
            'enderEmit': {
                'xLgr': self.company_id.street,
                'nro': self.company_id.number,
                'xCpl': self.company_id.street2 or '',
                'xBairro': self.company_id.district,
                'cMun': '%s%s' % (
                    self.company_id.partner_id.state_id.ibge_code,
                    self.company_id.partner_id.city_id.ibge_code),
                'xMun': self.company_id.city_id.name,
                'UF': self.company_id.state_id.code,
                'cPais': self.company_id.country_id.ibge_code,
                'xPais': self.company_id.country_id.name,
                'email': self.company_id.email,
                'fone': re.sub('[^0-9]', '', self.company_id.phone or '')
            },
        }
        #import pudb;pu.db
        infveiculos = []
        infreboques = []
        veictracao = {}
        infcondutores = []
        for condutor in self.condutor_ids:
            cpf = re.sub('[^0-9]', '', condutor.cnpj_cpf)
            infcondutores.append({
               'xNome' : condutor.name,
               'CPF' : cpf,
            })
        veictracao['condutor'] = infcondutores
        
        for veic in self.veiculo_ids:
            placa = veic.veiculo_id.name.replace('-','')
            if veic.veiculo_tipo == 0:
                veictracao['placa'] = placa
                veictracao['tara'] = int(veic.veiculo_id.tara_kg)
                veictracao['tpRod'] = veic.veiculo_id.tipo_rodado
                veictracao['tpCar'] = veic.veiculo_id.tipo_carroceria
                veictracao['UF'] = veic.veiculo_uf.code
                veictracao['capKG'] = int(veic.veiculo_id.capacidade_kg)
                veictracao['capM3'] = int(veic.veiculo_id.capacidade_m3)
                veictracao['cInt'] = veic.veiculo_id.id
                if veic.veiculo_renavam:
                    veictracao['RENAVAM'] = veic.veiculo_renavam
                #import pudb;pu.db
                infveiculos.append(veictracao)

            if veic.veiculo_tipo == 1:
                veicreboque = {
                    'placa' : placa,
                    'tara' : int(veic.veiculo_id.tara_kg),
                    'tpRod' : veic.veiculo_id.tipo_rodado,
                    'tpCar' : veic.veiculo_id.tipo_carroceria,
                    'UF' : veic.veiculo_uf.code,
                    'capKG' : int(veic.veiculo_id.capacidade_kg),
                    'capM3' : int(veic.veiculo_id.capacidade_m3),
                    'cInt' : veic.veiculo_id.id,
                }
                infreboques.append(veicreboque)    
            infANTT = {
                'RNTRC' : veic.veiculo_rntrc,
            }
        veicReboque = []
        if infreboques:
             veicReboque = infreboques[0]
        infModal =  {
                'rodo' : {
                'infANTT': infANTT,
                'veicTracao': infveiculos[0],
                'veicReboque' : veicReboque,
                }
        }

        #infDoc
        # NFe/CTe/MDFe

        #@@@@@@@@@@@@@@@@@
        doc_ids = []
        qtde_doc = 0
        valor_total = 0.0
        import pudb;pu.db
        for doc in self.document_related_ids:
            qtde_doc += 1
            valor_total += doc.valor
            ide['UFFim'] = doc.documento_municipio.state_id.code
            doc_ids = self._prepare_eletronic_docs_values(doc)

        # SEGURO
        for seg in self.seguro_ids:
            seguro = {
                'infResp': {
                    'respSeg': seg.responsavel_seguro,
                    }
                }
        self.valor_final = valor_total
        # TOT
        #import pudb;pu.db
        total = {
            'qNFe': qtde_doc,
            'vCarga': "%.02f" % self.valor_final,
            'cUnid': self.unidade_carga.zfill(2),
            'qCarga': "%.04f" % self.peso_bruto ,
        }
        #import pudb;pu.db
        lacre = {'nLacre': self.lacre_ids.name}
 
        #if self.ambiente_mdfe == '2':
        #    dest['xNome'] = \
        #        u'NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO -\
        #SEM VALOR FISCAL'

        autorizados = []
        if self.company_id.accountant_id:
            autorizados.append({
                'CNPJ': re.sub(
                    '[^0-9]', '', self.company_id.accountant_id.cnpj_cpf)
            })

        if self.transportadora_id.street:
            end_transp = "%s - %s, %s" % (self.transportadora_id.street,
                                          self.transportadora_id.number or '',
                                          self.
                                          transportadora_id.district or '')
        else:
            end_transp = ''
        transp = {
            'modFrete': self.modalidade_frete,
            'transporta': {
                'xNome': self.transportadora_id.legal_name or
                self.transportadora_id.name or '',
                'IE': re.sub('[^0-9]', '',
                             self.transportadora_id.inscr_est or ''),
                'xEnder': end_transp
                if self.transportadora_id else '',
                'xMun': self.transportadora_id.city_id.name or '',
                'UF': self.transportadora_id.state_id.code or ''
            },
            'veicTransp': {
                'placa': self.placa_veiculo or '',
                'UF': self.uf_veiculo or '',
                'RNTC': self.rntc or '',
            }
        }
        cnpj_cpf = re.sub('[^0-9]', '', self.transportadora_id.cnpj_cpf or '')
        if self.transportadora_id.is_company:
            transp['transporta']['CNPJ'] = cnpj_cpf
        else:
            transp['transporta']['CPF'] = cnpj_cpf

        reboques = []
        for item in self.reboque_ids:
            reboques.append({
                'placa': item.placa_veiculo or '',
                'UF': item.uf_veiculo or '',
                'RNTC': item.rntc or '',
                'vagao': item.vagao or '',
                'balsa': item.balsa or '',
            })
        transp['reboque'] = reboques
        volumes = []
        for item in self.volume_ids:
            volumes.append({
                'qVol': item.quantidade_volumes or '',
                'esp': item.especie or '',
                'marca': item.marca or '',
                'nVol': item.numeracao or '',
                'pesoL': "%.03f" % item.peso_liquido
                if item.peso_liquido else '',
                'pesoB': "%.03f" % item.peso_bruto if item.peso_bruto else '',
            })
        transp['vol'] = volumes

        responsavel_tecnico = self.company_id.responsavel_tecnico_id
        infRespTec = {}

        if responsavel_tecnico:
            if len(responsavel_tecnico.child_ids) == 0:
                raise UserError(
                    "Adicione um contato para o responsável técnico!")

            cnpj = re.sub('[^0-9]', '', responsavel_tecnico.cnpj_cpf)
            fone = re.sub('[^0-9]', '', responsavel_tecnico.phone or '')
            infRespTec = {
                'CNPJ': cnpj or '',
                'xContato': responsavel_tecnico.child_ids[0].name or '',
                'email': responsavel_tecnico.email or '',
                'fone': fone,
                'idCSRT': self.company_id.id_token_csrt or '',
                'hashCSRT': self._get_hash_csrt() or '',
            }
        # 'dest': dest,
        #'infAdic': infAdic,
        #'seg': seguro,
        vals = {
            'Id': '',
            'ide': ide,
            'emit': emit,
            'autXML': autorizados,
            'transp': transp,
            'infModal': infModal,
            'infDoc': doc_ids,
            'tot': total,
            'infRespTec': infRespTec,
        }
        #import pudb;pu.db
        #'infModal' : infModal,
        vals = [{       
            
                'infMDFe': vals,
        }]

        return vals

    @api.multi
    def _prepare_lote(self, lote, mdfe_values):
        if self.model == '58':
            return {
                'idLote': lote,
                'indSinc': 1 if self.company_id.nfe_sinc else 0,
                'estado': self.company_id.partner_id.state_id.ibge_code,
                'ambiente': int(self.ambiente_mdfe),
                'MDFes' : mdfe_values,
                'modelo': self.model,
            }
        else:
            return super(InvoiceEletronic, self)._prepare_lote(lote, mdfe_values)

    def _find_attachment_ids_email(self):
        atts = super(InvoiceEletronic, self)._find_attachment_ids_email()
        if self.model not in ('55'):
            return atts

        attachment_obj = self.env['ir.attachment']
        nfe_xml = base64.decodestring(self.nfe_processada)
        logo = base64.decodestring(self.invoice_id.company_id.logo)

        tmpLogo = io.BytesIO()
        tmpLogo.write(logo)
        tmpLogo.seek(0)

        xml_element = etree.fromstring(nfe_xml)
        oDanfe = danfe(list_xml=[xml_element], logo=tmpLogo)

        tmpDanfe = io.BytesIO()
        oDanfe.writeto_pdf(tmpDanfe)

        if danfe:
            danfe_id = attachment_obj.create(dict(
                name="Danfe-%08d.pdf" % self.numero,
                datas_fname="Danfe-%08d.pdf" % self.numero,
                datas=base64.b64encode(tmpDanfe.getvalue()),
                mimetype='application/pdf',
                res_model='account.invoice',
                res_id=self.invoice_id.id,
            ))
            atts.append(danfe_id.id)
        if nfe_xml:
            xml_id = attachment_obj.create(dict(
                name=self.nfe_processada_name,
                datas_fname=self.nfe_processada_name,
                datas=base64.encodestring(nfe_xml),
                mimetype='application/xml',
                res_model='account.invoice',
                res_id=self.invoice_id.id,
            ))
            atts.append(xml_id.id)
        return atts

    @api.multi
    def recriar_xml(self):
        self.write({
            'data_emissao': datetime.now(),
        })
        self.action_post_validate()

    @api.multi
    def action_post_validate(self):
        res = super(InvoiceEletronic, self).action_post_validate()
        if self.model not in ('58'):
            return res
        chave_dict = {
            'cnpj': re.sub('[^0-9]', '', self.company_id.cnpj_cpf),
            'estado': self.company_id.state_id.ibge_code,
            'emissao': self.data_emissao.strftime("%y%m"),
            'modelo': self.model,
            'numero': self.numero,
            'serie': self.serie.code.zfill(3),
            'tipo': int(self.tipo_emissao),
            'codigo': "%08d" % self.id
        }
        
        self.chave_nfe = gerar_chave_mdfe(ChaveMDFe(**chave_dict))

        cert = self.company_id.with_context(
            {'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)

        certificado = Certificado(
            cert_pfx, self.company_id.nfe_a1_password)

        nfe_values = self._prepare_eletronic_invoice_values()

        lote = self._prepare_lote(self.id, nfe_values)
        if self.model in ('55', '65'):
            xml_enviar = xml_autorizar_nfe(certificado, **lote)
            mensagens_erro = valida_nfe(xml_enviar)
        #import pudb;pu.db
        if self.model in ('58'):
            #xml_mdfe = xml_render_mdfe(certificado, **lote)
            xml_enviar = xml_render_mdfe(certificado, **lote)
            #return _send_v300(certificado, 'MDFeRecepcao', **kwargs)
            #self.sudo().write({
            #     'xml_to_send': base64.encodestring(xml_mdfe),
            #     'xml_to_send_name': 'mdfe-enviar-%s.xml' % self.numero,
            #})
            mensagens_erro = valida_mdfe(xml_enviar)
            if mensagens_erro:
                #print(mensagens_erro)
                raise UserError(mensagens_erro)
        
        #COMENTADO para TESTAR
        self.sudo().write({
            'xml_to_send': base64.encodestring(xml_enviar),
            'xml_to_send_name': 'mdfe-enviar-%s.xml' % self.numero,
        })

    @api.multi
    def action_send_eletronic_invoice(self):
        import pudb;pu.db
        super(InvoiceEletronic, self).action_send_eletronic_invoice()
        
        if self.model not in ('58') or self.state in (
           'done', 'denied', 'cancel'):
            return

        _logger.info('Sending MDF-e (%s) (%.2f) - %s' % (
            self.numero, self.valor_final, self.partner_id.name))
        self.write({
            'state': 'error',
            'data_emissao': datetime.now()
        })

        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)
        #import pudb;pu.db
        certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)
        
        xml_to_send = base64.decodestring(self.xml_to_send).decode('utf-8')

        resposta_recibo = None
        resposta = autorizar_mdfe(
            certificado, xml=xml_to_send,
            estado=self.company_id.state_id.ibge_code,
            ambiente=int(self.ambiente_mdfe),
            modelo=self.model)
        retorno = resposta['object'].getchildren()[0]
        if retorno.cStat == 103:
            obj = {
                'estado': self.company_id.partner_id.state_id.ibge_code,
                'ambiente': int(self.ambiente_mdfe),
                'obj': {
                    'ambiente': int(self.ambiente_mdfe),
                    'numero_recibo': retorno.infRec.nRec
                },
                'modelo': self.model,
            }
            self.recibo_nfe = obj['obj']['numero_recibo']
            import time
            while True:
                time.sleep(2)
                resposta_recibo = retorno_autorizar_mdfe(certificado, **obj)
                retorno = resposta_recibo['object'].getchildren()[0]
                if retorno.cStat != 105:
                    break

        if retorno.cStat != 104:
            self.write({
                'codigo_retorno': retorno.cStat,
                'mensagem_retorno': retorno.xMotivo,
            })
            self.notify_user()
        else:
            self.write({
                'codigo_retorno': retorno.protMDFe.infProt.cStat,
                'mensagem_retorno': retorno.protMDFe.infProt.xMotivo,
            })
            if self.codigo_retorno == '100':
                self.write({
                    'state': 'done',
                    'protocolo_nfe': retorno.protMDFe.infProt.nProt,
                    'data_autorizacao': retorno.protMDFe.infProt.dhRecbto
                })
            #else:
            #    self.notify_user()
            # Duplicidade de NF-e significa que a nota já está emitida
            # TODO Buscar o protocolo de autorização, por hora só finalizar
            if self.codigo_retorno == '204':
                self.write({
                    'state': 'done', 'codigo_retorno': '100',
                    'mensagem_retorno': 'Autorizado o uso da MDF-e'
                })

            # Denegada e nota já está denegada
            if self.codigo_retorno in ('302', '205'):
                self.write({'state': 'denied'})

        self.env['invoice.eletronic.event'].create({
            'code': self.codigo_retorno,
            'name': self.mensagem_retorno,
            'invoice_eletronic_id': self.id,
        })
        self._create_attachment('mdfe-envio', self, resposta['sent_xml'])
        self._create_attachment('mdfe-ret', self, resposta['received_xml'])
        recibo_xml = resposta['received_xml']
        if resposta_recibo:
            self._create_attachment('rec', self, resposta_recibo['sent_xml'])
            self._create_attachment('rec-ret', self,
                                    resposta_recibo['received_xml'])
            recibo_xml = resposta_recibo['received_xml']

        if self.codigo_retorno == '100':
            mdfe_proc = gerar_mdfeproc(resposta['sent_xml'], recibo_xml)
            self.sudo().write({
                'nfe_processada': base64.encodestring(mdfe_proc),
                'nfe_processada_name': "MDFe%08d.xml" % self.numero,
            })
        _logger.info('MDF-e (%s) was finished with status %s' % (
            self.numero, self.codigo_retorno))

    @api.multi
    def generate_nfe_proc(self):
        if self.state in ['cancel', 'done', 'denied']:
            recibo = self.env['ir.attachment'].search([
                ('res_model', '=', 'invoice.eletronic'),
                ('res_id', '=', self.id),
                ('datas_fname', 'like', 'rec-ret')], limit=1)
            if not recibo:
                recibo = self.env['ir.attachment'].search([
                    ('res_model', '=', 'invoice.eletronic'),
                    ('res_id', '=', self.id),
                    ('datas_fname', 'like', 'nfe-ret')], limit=1)
            nfe_envio = self.env['ir.attachment'].search([
                ('res_model', '=', 'invoice.eletronic'),
                ('res_id', '=', self.id),
                ('datas_fname', 'like', 'nfe-envio')], limit=1)
            if nfe_envio.datas and recibo.datas:
                nfe_proc = gerar_nfeproc(
                    base64.decodestring(nfe_envio.datas).decode('utf-8'),
                    base64.decodestring(recibo.datas).decode('utf-8'),
                )
                self.sudo().write({
                    'nfe_processada': base64.encodestring(nfe_proc),
                    'nfe_processada_name': "NFe%08d.xml" % self.numero,
                })
        else:
            raise UserError(_('A NFe não está validada'))

    @api.multi
    def action_cancel_document(self, context=None, justificativa=None):
        if self.model not in ('55', '65'):
            return super(InvoiceEletronic, self).action_cancel_document(
                justificativa=justificativa)

        if not justificativa:
            return {
                'name': _('Cancelamento NFe'),
                'type': 'ir.actions.act_window',
                'res_model': 'wizard.cancel.nfe',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_edoc_id': self.id
                }
            }

        _logger.info('Cancelling NF-e (%s)' % self.numero)
        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)
        certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)

        id_canc = "ID110111%s%02d" % (
            self.chave_nfe, self.sequencial_evento)

        tz = timezone(self.env.user.tz)
        dt_evento = datetime.now(tz).replace(microsecond=0).isoformat()

        cancelamento = {
            'idLote': self.id,
            'estado': self.company_id.state_id.ibge_code,
            'ambiente': int(self.ambiente_mdfe),
            'eventos': [{
                'Id': id_canc,
                'cOrgao': self.company_id.state_id.ibge_code,
                'tpAmb': int(self.ambiente_mdfe),
                'CNPJ': re.sub('[^0-9]', '', self.company_id.cnpj_cpf),
                'chNFe': self.chave_nfe,
                'dhEvento': dt_evento,
                'nSeqEvento': self.sequencial_evento,
                'nProt': self.protocolo_nfe,
                'xJust': justificativa,
                'tpEvento': '110111',
                'descEvento': 'Cancelamento',
            }],
            'modelo': self.model,
        }

        resp = recepcao_evento_cancelamento(certificado, **cancelamento)
        resposta = resp['object'].getchildren()[0]
        if resposta.cStat == 128 and \
                resposta.retEvento.infEvento.cStat in (135, 136, 155):
            self.write({
                'state': 'cancel',
                'codigo_retorno': resposta.retEvento.infEvento.cStat,
                'mensagem_retorno': resposta.retEvento.infEvento.xMotivo,
                'sequencial_evento': self.sequencial_evento + 1,
            })
        else:
            code, motive = None, None
            if resposta.cStat == 128:
                code = resposta.retEvento.infEvento.cStat
                motive = resposta.retEvento.infEvento.xMotivo
            else:
                code = resposta.cStat
                motive = resposta.xMotivo
            if code == 573:  # Duplicidade, já cancelado
                return self.action_get_status()

            return self._create_response_cancel(
                code, motive, resp, justificativa)

        self.env['invoice.eletronic.event'].create({
            'code': self.codigo_retorno,
            'name': self.mensagem_retorno,
            'invoice_eletronic_id': self.id,
        })
        self._create_attachment('canc', self, resp['sent_xml'])
        self._create_attachment('canc-ret', self, resp['received_xml'])
        nfe_processada = base64.decodestring(self.nfe_processada)

        nfe_proc_cancel = gerar_nfeproc_cancel(
            nfe_processada, resp['received_xml'].encode())
        if nfe_proc_cancel:
            self.nfe_processada = base64.encodestring(nfe_proc_cancel)
        _logger.info('Cancelling NF-e (%s) was finished with status %s' % (
            self.numero, self.codigo_retorno))

    def action_get_status(self):
        if self.model not in ('58'):
            return super(InvoiceEletronic, self).action_get_status()
        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)
        certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)
        consulta = {
            'estado': self.company_id.state_id.ibge_code,
            'ambiente': int(self.ambiente_mdfe),
            'modelo': self.model,
            'obj': {
                'numero_recibo': self.chave_nfe,
                'ambiente': int(self.ambiente_mdfe),
            }
        }
        resp = consulta_situacao_mdfe(certificado, **consulta)
        retorno_consulta = resp['object'].getchildren()[0]

        if retorno_consulta.cStat == 101:
            self.state = 'cancel'
            self.codigo_retorno = retorno_consulta.cStat
            self.mensagem_retorno = retorno_consulta.xMotivo
            resp['received_xml'] = etree.tostring(
                retorno_consulta, encoding=str)

            self.env['invoice.eletronic.event'].create({
                'code': self.codigo_retorno,
                'name': self.mensagem_retorno,
                'invoice_eletronic_id': self.id,
            })
            self._create_attachment('canc', self, resp['sent_xml'])
            self._create_attachment('canc-ret', self, resp['received_xml'])
            nfe_processada = base64.decodestring(self.nfe_processada)

            nfe_proc_cancel = gerar_mdfeproc_cancel(
                nfe_processada, resp['received_xml'].encode())
            if nfe_proc_cancel:
                self.sudo().write({
                    'mdfe_processada': base64.encodestring(nfe_proc_cancel),
                })
        elif retorno_consulta.cStat == 100:
            #self.action_post_validate()
            #mdfe_processada = base64.decodestring(self.xml_to_send).decode('utf-8')
            #mde_proc = gerar_mdfeproc(mdfe_processada, resp['received_xml'])
            #self.nfe_processada = base64.encodestring(mdfe_proc)
            #self.nfe_processada_name = "MDFe%08d.xml" % self.numero
            message = "%s - %s" % (retorno_consulta.cStat,
                                   retorno_consulta.xMotivo)
            self.mensagem_retorno = message
            self.codigo_retorno = retorno_consulta.cStat
            self.state = 'done'
        else:
            message = "%s - %s" % (retorno_consulta.cStat,
                                   retorno_consulta.xMotivo)
            raise UserError(message)

    def _create_response_cancel(self, code, motive, response, justificativa):
        message = "%s - %s" % (code, motive)
        wiz = self.env['wizard.cancel.nfe'].create({
            'edoc_id': self.id,
            'justificativa': justificativa,
            'state': 'error',
            'message': message,
            'sent_xml': base64.b64encode(
                response['sent_xml'].encode('utf-8')),
            'sent_xml_name': 'cancelamento-envio.xml',
            'received_xml': base64.b64encode(
                response['received_xml'].encode('utf-8')),
            'received_xml_name': 'cancelamento-retorno.xml',
        })
        return {
            'name': _('Cancelamento NFe'),
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.cancel.nfe',
            'res_id': wiz.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_hash_csrt(self):
        chave_nfe = self.chave_nfe
        csrt = self.company_id.csrt

        if not csrt:
            return

        hash_csrt = "{0}{1}".format(csrt, chave_nfe)
        hash_csrt = base64.b64encode(
            hashlib.sha1(hash_csrt.encode()).digest())

        return hash_csrt.decode("utf-8")
