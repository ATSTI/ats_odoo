# -*- coding:utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError
from datetime import datetime
from datetime import date
from datetime import timedelta
from unidecode import unidecode
import logging
import psycopg2
import re
import os
import json
from . import atscon as con


_logger = logging.getLogger(__name__)

class PosSession(models.Model):
    _inherit = 'pos.session'
    
    venda_finalizada = fields.Boolean(string='Vendas Finalizadas')
    msg_integracao = fields.Html(string='Executando')
    periodo_integracao = fields.Integer(string='Periodo Integração', default=1)
    integracao_andamento = fields.Datetime(string='Data Integracao', default=fields.Datetime.now)
    
    @api.multi
    def action_pos_session_closing_control(self):
        if self.venda_finalizada:
            super(PosSession, self).action_pos_session_closing_control()
        else:
            raise UserError(
                    u'Encerre o Caixa no PDV.')

    def cron_integra_caixas(self):
        session_ids = self.env['pos.session'].search([
                ('state', '=', 'opened')])
        for ses in session_ids:
             self.action_atualiza_caixas(ses)

    def action_integra_caixas(self):
        # se nao for no pos enviar email com as msg_erro
        self.msg_integracao = self.action_atualiza_caixas(self)
    
    def action_atualiza_caixas(self, session):
        try:
            if session.config_id.ip_terminal:
                db = con.Conexao(session.config_id.ip_terminal, session.config_id.database)
            else:
                return False
        except:
            msg_sis = u'Caminho ou nome do banco inválido.<br>'
        msg_erro = ''
        msg_sis = 'Integrando Caixa com o PDV<br>'
        hj = datetime.now()
        hj = hj - timedelta(days=self.periodo_integracao)
        hj = datetime.strftime(hj,'%Y-%m-%d %H:%M:%S')
        user_ids = self.env['res.users'].search([('write_date', '>=', hj)])
        for usr in user_ids:
            sqlp = 'SELECT CODUSUARIO FROM USUARIO where CODUSUARIO = %s' %(str(usr.id))
            usrq = db.query(sqlp)
            if not len(usrq):
                barcode = ''
                if usr.barcode:
                    barcode = usr.barcode
                #log = 'Cadastrando Usuario novo : %s\n' %(usr.name.encode('ascii', 'ignore').decode('ascii'))
                #arq.write(log)
                insere = 'INSERT INTO USUARIO (CODUSUARIO, NOMEUSUARIO, '
                insere += 'STATUS, PERFIL, SENHA, CODBARRA) VALUES ('
                insere += '%s'
                insere += ',\'%s\''
                insere += ', 1'
                insere += ',\'CAIXA\''
                insere += ',\'CAIXA\''
                insere += ',\'%s\');'
                insere = insere %(str(usr.id), str(usr.name), str(barcode))
                db.insert(insere)

        sessao_ids = self.env['pos.session'].search([
            ('create_date', '>=', hj),
            ])
        #('state','=','opened')
        for ses in sessao_ids:           
            sqlp = 'SELECT CODCAIXA, SITUACAO FROM CAIXA_CONTROLE where CODCAIXA = %s' %(str(ses.id))
            sess = db.query(sqlp)
            if not len(sess):
                #state = 'c' # close
                #if ses.state == 'opened':
                #dta_abre = '%s.%s.%s' %(str(ses.start_at.month).zfill(2), str(ses.start_at.day).zfill(2), str(ses.start_at.year))
                hj = datetime.now()
                dta_abre = datetime.strftime(hj,'%m-%d-%Y')
                if ses.start_at:
                    dta_abre = '%s/%s/%s' %(str(ses.start_at[5:7]), str(ses.start_at[8:10]), str(ses.start_at[:4]))
                state = 'o'
                insere = 'INSERT INTO CAIXA_CONTROLE (IDCAIXACONTROLE, '
                insere += 'CODCAIXA, CODUSUARIO, SITUACAO, DATAFECHAMENTO'
                insere += ',NOMECAIXA, DATAABERTURA) VALUES ('
                insere += '%s'
                insere += ',%s'
                insere += ',%s'
                insere += ',\'%s\''
                insere += ',\'%s\''
                insere += ',\'%s\''
                insere += ',\'%s\');'
                
                insere = insere %(str(ses.id), str(ses.id), str(ses.user_id.id), str(state) \
                ,str('01.01.2018'), str(ses.name), str(dta_abre))
                db.insert(insere)
            else:
                #if ses.state != 'opened':
                #    altera = 'UPDATE CAIXA_CONTROLE SET SITUACAO = \'F\''
                #    altera += ' WHERE IDCAIXACONTROLE = %s' %(str(ses.id))
                #    db.insert(altera)

                if sess[0][1] == 'F':
                    ses.venda_finalizada = True

    def cron_integra_produtos(self):
        session_ids = self.env['pos.session'].search([
                ('state', '=', 'opened')])
        #for ses in session_ids:
        self.action_atualiza_produtos(session_ids[0])

    def action_integra_produtos(self):
        # se nao for no pos enviar email com as msg_erro
        self.msg_integracao = self.action_atualiza_produtos(self)

    def action_atualiza_produtos(self, session):
        #try:
        #    if session.config_id.ip_terminal:
        #        db = con.Conexao(session.config_id.ip_terminal, session.config_id.database)
        #    else:
        #        return False
        #except:
        #    msg_sis = u'Caminho ou nome do banco inválido.<br>'
        msg_erro = ''
        msg_sis = 'Integrando Produtos para o PDV<br>'
        hj = datetime.now()
        hj = hj - timedelta(days=self.periodo_integracao)
        hj = datetime.strftime(hj,'%Y-%m-%d %H:%M:%S')
        prod_tmpl = self.env['product.template'].search([
            ('write_date', '>=', hj),
            ('sale_ok', '=', True)])
        prod_ids = []
        import pudb;pu.db
        prd_ids = set()
        for pr in prod_tmpl:
            prd_ids.add(pr.id)
        if prod_tmpl:
            prod_ids = self.env['product.product'].search([
                ('product_tmpl_id','in',list(prd_ids))])
            msg_sis += 'Qtde de Produtos %s para importar/atualizar<br>' %(str(len(prod_ids)))
        else:
            msg_sis += 'Sem produtos pra importar/atualizar<br>'
        #print ('Qtde de Produtos %s\n' %(str(len(prod_ids))))
        lista = []
        for prd in prod_ids:
            prod = {}
            ncm = ''
            if prd.fiscal_classification_id:
                ncm = prd.fiscal_classification_id.code
                if ncm:
                    ncm = re.sub('[^0-9]', '', ncm)
            if ncm and len(ncm) > 8:
                ncm = '00000000'
            
            prod['CODPRODUTO'] = prd.id
            prod['UNIDADEMEDIDA'] = prd.uom_id.name.strip()
            produto = prd.name.strip()
            produto = produto.replace("'"," ")
            produto = unidecode(produto)
            prod['PRODUTO'] = produto
            prod['VALOR_PRAZO'] = prd.list_price
            prod['CODPRO'] = prd.default_code.strip()
            prod['ORIGEM'] = prd.origin
            prod['NCM'] = ncm
            if prd.barcode and len(prd.barcode) < 14:
                prod['COD_BARRA'] = prd.barcode.strip()
            lista.append(prod)
        with open(session.config_id.database+'produto.txt', 'w') as f:
            f.write(json.dumps(lista))
        f.close            
            
        return True 
        
        # daqui pra baixo era a versao q inseria no firebird   
            
        if not lista:
            
            #if not product_id.origin:
            #    continue
            #print ('Produto %s\n' %(str(product_id.product_tmpl_id.id)))
            p_custo = 0.0
            if product_id.standard_price:
                p_custo = product_id.standard_price
            p_venda = 0.0
            if product_id.list_price:
                p_venda = product_id.list_price
            codbarra = ''
            if product_id.barcode and len(product_id.barcode) < 14:
                codbarra = product_id.barcode.strip()
            produto = product_id.name.strip()
            produto = produto.replace("'"," ")
            produto = unidecode(produto)
            sqlp = 'select codproduto from produtos where codproduto = %s' %(product_id.id)
            prods = db.query(sqlp)
            codp = str(product_id.id)
            if product_id.default_code:
                codp = product_id.default_code.strip()
            if not len(prods):
                #print ('Incluindo - %s' %(product_id.name))
                sqlp = 'select codproduto from produtos where codpro like \'%s\'' %(codp+'%')
                
                prodsa = db.query(sqlp)					
                if len(prodsa):
                    if product_id.default_code:
                        codp = product_id.default_code + '(%s)' %(str(len(prodsa)+1))
                if len(codp) > 14:
                    codp = str(product_id.id) 
                #print ('Incluindo - %s-%s' %(str(product_id.id),product_id.name))
                un = product_id.uom_id.name
                insere = 'INSERT INTO PRODUTOS (CODPRODUTO, UNIDADEMEDIDA, PRODUTO, PRECOMEDIO, CODPRO,\
                          TIPOPRECOVENDA, ORIGEM, NCM, VALORUNITARIOATUAL, VALOR_PRAZO, TIPO, RATEIO, \
                          QTDEATACADO, PRECOATACADO'
                if codbarra:
                    insere += ', COD_BARRA'
                insere += ') VALUES ('
                insere += str(product_id.id)
                insere += ', \'' + un + '\''
                insere += ', \'' + produto + '\''
                insere += ',' + str(p_custo)
                insere += ', \'' + str(codp) + '\''
                insere += ',\'F\''
                insere += ',' + str(product_id.origin)
                insere += ',\'' + str(ncm) + '\''
                insere += ',' + str(p_custo)
                insere += ',' + str(p_venda)
                insere += ',\'' + str('PROD') + '\''
                insere += ', \'' + product_id.tipo_venda + '\''
                insere += ',' + str(product_id.qtde_atacado)
                insere += ',' + str(product_id.preco_atacado)
                if codbarra:
                    insere += ', \'' + str(codbarra) + '\''
                insere += ')'
                #print (codp+'-'+produto)
                retorno = db.insert(insere)
                # TODO tratar isso e enviar email
                if retorno:
                    msg_erro += 'ERRO : %s<br>' %(retorno)
                #    print ('SQL %s' %str(insere))
            else:
                #print ('Alterando - %s' %(product_id.name))
                altera = 'UPDATE PRODUTOS SET PRODUTO = '
                altera += '\'' + produto + '\''
                altera += ', VALOR_PRAZO = ' + str(p_venda)
                altera += ', NCM = ' +  '\'' + str(ncm) + '\''
                altera += ', ORIGEM = ' + str(product_id.origin) 
                altera += ', RATEIO = \'' + str(product_id.tipo_venda) + '\''
                altera += ', QTDEATACADO = ' + str(product_id.qtde_atacado) 
                altera += ', PRECOATACADO = ' + str(product_id.preco_atacado) 
                if codbarra:
                    altera += ', COD_BARRA = \'' + str(codbarra) + '\''
                altera += ' WHERE CODPRODUTO = ' + str(product_id.id)
                retorno = db.insert(altera)
                if retorno:
                    msg_erro += 'ERRO : %s<br>' %(retorno)
        #print ('Integracao realizada com sucesso.')
        msg_sis += 'Integracao Finalizada.<br>'
        return msg_sis + '<br>' + msg_erro

    def cron_integra_clientes(self):
        session_ids = self.env['pos.session'].search([
                ('state', '=', 'opened')])
        #for ses in session_ids:
        self.action_atualiza_clientes(session_ids[0])

    def action_integra_clientes(self):
        # se nao for no pos enviar email com as msg_erro
        self.msg_integracao = self.action_atualiza_clientes(self)

    def action_atualiza_clientes(self, session):  
        #try:
        #    if session.config_id.ip_terminal:
        #        db = con.Conexao(session.config_id.ip_terminal, session.config_id.database)
        #    else:
        #        return False
        #except:
        #    msg_sis = u'Caminho ou nome do banco inválido.<br>'
        import pudb;pu.db
        msg_erro = ''
        msg_sis = 'Integrando Clientes para o PDV<br>'
        hj = datetime.now()
        hj = hj - timedelta(days=session.periodo_integracao)
        hj = datetime.strftime(hj,'%Y-%m-%d %H:%M:%S')
        cliente = self.env['res.partner']
        cli_ids = cliente.search([('write_date', '>=', hj), ('customer','=', True)])
        lista = []
        for partner_id in cli_ids:
            cliente = {}
            nome = partner_id.name.strip()
            nome = nome.replace("'"," ")
            nome = unidecode(nome)
            cliente['codcliente'] = partner_id.id
            cliente['nomecliente'] = nome
            cliente['razaosocial'] = nome
            cliente['cnpj'] = partner_id.cnpj_cpf
            lista.append(cliente)
        with open(session.config_id.database+'cliente.txt', 'w') as f:
            f.write(json.dumps(lista))
        f.close
        return 
        """
            if arq != '':
                arq += ', '
            arq += '{"CODCLIENTE": "%s", "NOMECLIENTE": "%s","RAZAOSOCIAL": "%s" \
                , "TIPOFIRMA": "1", "CNPJ": "%s", "INSCESTADUAL": "%s" \
                , "SEGMENTO": "1", "REGIAO": "1", "LIMITECREDITO": "1" \
                , "DATACADASTRO": "%s", "CODUSUARIO": "1", "STATUS": "1" \
                , "CODBANCO": "1", "CODFISCAL": "1"}'
        """
            
        x = 0
        if x == 1:
            
            sqlc = 'select codcliente from clientes where codcliente = %s' %(partner_id.id)
            cli = db.query(sqlc)
            nome = partner_id.name.strip()
            nome = nome.replace("'"," ")
            nome = unidecode(nome)
            
            if partner_id.legal_name:
                razao = partner_id.legal_name.strip()
                razao = razao.replace("'"," ")
                razao = unidecode(razao)
            else:
                razao = nome
            if not len(cli):
                tipo = '0'
                if partner_id.is_company:
                    tipo = '1'
                vendedor = '1'
                if partner_id.user_id.id:
                    vendedor = str(partner_id.user_id.id)
                ie = ''
                if partner_id.inscr_est:
                    ie = partner_id.inscr_est
                fiscal = 'J'
                
                regiao = '0'
                if partner_id.curso:
                    regiao = '1'
                insere = 'insert into clientes (\
                            CODCLIENTE, NOMECLIENTE, RAZAOSOCIAL,\
                            TIPOFIRMA,CNPJ, INSCESTADUAL,\
                            SEGMENTO, REGIAO, LIMITECREDITO,\
                            DATACADASTRO, CODUSUARIO, STATUS, CODBANCO, CODFISCAL)\
                            values (%s, \'%s\', \'%s\',\
                            %s, \'%s\',\'%s\',\
                            %s, %s, %s,\
                            %s, %s, %s, %s, \'%s\')'\
                            %(str(partner_id.id), nome, razao, \
                            tipo, partner_id.cnpj_cpf, ie,\
                            '1', regiao, '0.0',\
                            'current_date', vendedor, '1', '1', fiscal)
                retorno = db.insert(insere)
                if retorno:
                    msg_erro += 'ERRO : %s<br>' %(retorno)                
                
                fone = 'Null'
                ddd = 'Null'
                if partner_id.phone:
                    fone = '''%s''' %(partner_id.phone[4:])
                    ddd = '''%s''' %(partner_id.phone[1:3])
                fone1 = 'Null'
                ddd1 = 'Null'
                if partner_id.mobile:
                    fone1 = '''%s''' %(partner_id.mobile[4:])
                    ddd1 = partner_id.mobile[1:3]
                fone2 = 'Null'
                ddd2 = 'Null'
                #if partner_id.fax:
                #    fone2 = partner_id.fax[4:]
                #    ddd2 = partner_id.fax[1:3]
                #buscar Cidade/UF/Pais
                cidade = 'Null'
                ibge = 'Null'
                uf = 'Null'
                pais = 'Null'
                if partner_id.city_id:
                    cidade = partner_id.city_id.name[:39]
                    if partner_id.city_id.ibge_code:
                        ibge = '%s%s-%s' %(partner_id.city_id.state_id.ibge_code, \
                                      partner_id.city_id.ibge_code[:4], \
                                      partner_id.city_id.ibge_code[4:])
                    uf = partner_id.city_id.state_id.code
                    pais = partner_id.city_id.state_id.country_id.name
                endereco = 'Null'
                if partner_id.street:
                    endereco = partner_id.street[:49]
                bairro = 'Null'
                if partner_id.district:
                    bairro = partner_id.district[:29]
                complemento = 'Null'
                if partner_id.street2:
                    complemento = partner_id.street2[:29]
                cep = 'Null'
                if partner_id.zip:
                    cep = '%s-%s' %(partner_id.zip[:5], \
                                    partner_id.zip[5:])
                    cep = cep[:10]
                email = 'Null'
                if partner_id.email:
                    email = partner_id.email[:255]
                obs = 'Null'
                if partner_id.comment:
                    obs = partner_id.comment[:199]
                numero = 'Null'
                if partner_id.number:
                    numero = partner_id.number[:5]
                inserir = 'INSERT INTO ENDERECOCLIENTE (CODENDERECO, \
                          CODCLIENTE, LOGRADOURO, BAIRRO, COMPLEMENTO,\
                          CIDADE, UF, CEP, TELEFONE, TELEFONE1, TELEFONE2,\
                          E_MAIL, TIPOEND,\
                          DADOSADICIONAIS, DDD, DDD1, DDD2,\
                          NUMERO, CD_IBGE, PAIS) VALUES ('
                inserir += str(partner_id.id)
                inserir += ',' + str(partner_id.id)
                if endereco != 'Null':
                    inserir += ', \'%s\'' %(str(endereco.encode('ascii', 'ignore')))
                else:
                    inserir += ', Null'
                if bairro != 'Null':
                    inserir += ', \'%s\'' % (str(bairro.encode('ascii', 'ignore')))
                else:
                    inserir += ', Null'
                if complemento != 'Null':
                    inserir += ', \'%s\'' % (str(complemento.encode('ascii', 'ignore')))
                else:
                    inserir += ', Null'
                if cidade != 'Null':
                    inserir += ', \'%s\'' % (str(cidade.encode('ascii', 'ignore')))
                else:
                    inserir += ', Null'
                if uf != 'Null':
                    inserir += ', \'%s\'' % (str(uf))
                else:
                    inserir += ', Null'
                if cep != 'Null':
                    inserir += ', \'%s\'' % (cep)
                else:
                    inserir += ', Null'
                if fone != 'Null':
                    inserir += ', \'%s\'' % (fone)
                else:
                    inserir += ', Null'
                if fone1 != 'Null':
                    inserir += ', \'%s\'' % (fone1)
                else:
                    inserir += ', Null'
                if fone2 != 'Null':
                    inserir += ', \'%s\'' % (fone2)
                else:
                    inserir += ', Null'
                if email != 'Null':
                    inserir += ', \'%s\'' % (email)
                else:
                    inserir += ', Null'
                inserir += ', 0' # tipoEnd
                if obs != 'Null':
                    inserir += ', \'%s\'' % (str(obs.encode('ascii', 'ignore')))
                else:
                    inserir += ', Null'
                if ddd != 'Null':
                    inserir += ', \'%s\'' % (ddd)
                else:
                    inserir += ', Null'
                if ddd1 != 'Null':
                    inserir += ', \'%s\'' % (ddd1)
                else:
                    inserir += ', Null'
                if ddd2 != 'Null':
                    inserir += ', \'%s\'' % (ddd2)
                else:
                    inserir += ', Null'
                if numero != 'Null':
                    inserir += ', \'%s\'' % (numero)
                else:
                    inserir += ', Null'
                if ibge != 'Null':
                    inserir += ', \'%s\'' % (ibge)
                else:
                    inserir += ', Null'
                if pais != 'Null':
                    inserir += ', \'%s\');' % (pais)
                else:
                    inserir += ', Null);'
                
                retorno = db.insert(inserir)
                if retorno:
                    msg_erro += 'ERRO : %s<br>' %(retorno)
            else:
                regiao = '0'
                if partner_id.curso:
                    regiao = '1'
                altera =  'UPDATE CLIENTES SET REGIAO = %s \
                    ,NOMECLIENTE = \'%s\', STATUS = 1 \
                    WHERE CODCLIENTE = %s' %(regiao, nome, str(partner_id.id))
                retorno = db.insert(altera )
                if retorno:
                    msg_erro += 'ERRO : %s<br>' %(retorno)
        
        msg_sis += 'Integracao Finalizada.<br>'
        return  msg_sis + '<br>' + msg_erro

    def cron_integra_vendas(self):
        session_ids = self.env['pos.session'].search([
                ('state', '=', 'opened')])
        #for ses in session_ids:
        #    if self.verifica_se_esta_rodando(ses):
        #        ses.integracao_andamento = datetime.strftime(datetime.now(),'%Y-%m-%d %H:%M:%S')
        self.action_atualiza_vendas(session_ids[0])

    def action_integra_vendas(self):
        # se nao for no pos enviar email com as msg_erro
        if self.verifica_se_esta_rodando(self):
            self.integracao_andamento = datetime.strftime(datetime.now(),'%Y-%m-%d %H:%M:%S')
            self.msg_integracao = self.action_atualiza_vendas(self)
        else:
            raise UserError(
                    u'Já existe Atualização em Andamento, aguarde.')
        
    def verifica_se_esta_rodando(self, session):
        hj = datetime.now()
        hj = hj - timedelta(minutes=1)
        hora = datetime.strptime(session.integracao_andamento,'%Y-%m-%d %H:%M:%S')
        if (hora < hj):
            return True
        else:
            return False


    def action_atualiza_vendas(self, session):
        #try:
        #    if session.config_id.ip_terminal:
        #        db = con.Conexao(session.config_id.ip_terminal, session.config_id.database)
        #    else:
        #        return False
        #except:
        #    msg_sis = u'Caminho ou nome do banco inválido.<br>'
        msg_erro = ''
        msg_sis = 'Integrando Vendas para o PDV<br>'
        hj = datetime.now()
        #hj = hj - timedelta(days=session.periodo_integracao)
        hj = datetime.strftime(hj,'%m-%d-%Y')
        caixa_usado = 'None'
        path_arquivos = '/home/publico/tmp/integra/'
        cod_cli = 1
        dt_mov = '2020.01.01'
        ord_name = ''
        pos_ord = self.env['pos.order']
        for _, _, arquivos in os.walk(path_arquivos):
            #import pudb;pu.db
            for arquivo in arquivos:
                if 'mov' in arquivo:
                    nome_arq = arquivo[4:]
                else:
                    continue
                arq = '%smov_%s' %(path_arquivos, nome_arq)
                mov_arquivo = arq
                if arq:
                    with open(arq) as movimento:
                        dados = json.load(movimento)
                        cod_mov = dados['CODMOVIMENTO']
                        cod_cli = dados['CODCLIENTE']
                        dt_mov = dados['DATA_SISTEMA']
                        cod_user = dados['CODVENDEDOR']
                        caixa = dados['CODALMOXARIFADO']
                        session = self.env['pos.session'].search([
                            ('id', '=', caixa)])
                        user_id = self.env['res.users'].search([
                            ('id','=', cod_user),
                        ])
                        if not user_id:
                            cod_user = 1       
                        ord_name = '%s-%s' %(str(session.id),cod_mov)
                        ord_ids = self.env['pos.order'].search([
                            ('session_id','=',session.id),
                            ('pos_reference','=',ord_name),
                        ])
                        if ord_ids:
                            continue
                        #msg_sis = 'Pedidos novos : %s<br>' %(str(mvs[0]))
                        caixa_usado = session.name
                        teve_desconto = 'n'
                        dt_ord = '2018.01.01'
                        msg_sis = 'Importando : %s<br>' %(cod_mov)
                        
                        vals = {}
                        vals['name'] = ord_name
                        vals['nb_print'] = 0
                        vals['pos_reference'] = ord_name
                        vals['session_id'] = session.id
                        #vals['pos_session_id'] = mvs[6]
                        vals['pricelist_id'] = session.config_id.pricelist_id.id
                        #vals['create_date'] = dt_mov #datetime.strftime(datetime.now(),'%Y-%m-%d %H:%M:%S')
                        vals['date_order'] = dt_mov
                        vals['sequence_number'] = cod_mov                
                        #if cli != 1:
                        cli = self.env['res.partner'].search([
                        ('id','=',cod_cli)],limit=1)
                        if not cli:
                            cod_cli = self.env['res.partner'].search([
                                ('name','ilike','consumidor')],limit=1).id
                        vals['partner_id'] = cod_cli
                        #userid = cod_user
                        #if mvs[5] == 2:
                        #    userid = 1
                        vals['user_id'] = cod_user
                        vals['fiscal_position_id'] = session.config_id.default_fiscal_position_id.id
                        vals['amount_tax'] = 0.0
                arq = '%spag_%s' %(path_arquivos, nome_arq)
                pag_arquivo = arq
                faturamento = 'n'
                teve_desconto = 'n'
                desconto_t = 0.0
                desco = 0.0
                if arq:
                    with open(arq) as pagamento:
                        dados = json.load(pagamento)
                        pag_line = []
                        
                        total_g = 0.0
                        troca = 0.0                             
                        vlr_pago = 0.0
                        for item in dados:
                            ver_json = json.loads(dados[item])
                            for det in ver_json:
                                vlr_pago = float(det['VALOR_PAGO'].replace(',','.'))
                                forma_pgto = det['FORMA_PGTO'].strip()
                                cod_mov = det['CODMOVIMENTO']
                                desco = float(det['DESCONTO'].replace(',','.'))
                                pag = {}
                                controle_troca = 0
                                if desco:
                                    desconto_t += desco
                                    teve_desconto = 's'
                                total_g += vlr_pago
                                jrn = '%s-' %(forma_pgto)
                                if jrn == '5-':
                                    jrn = '1-'
                                if jrn == '9-':
                                    troca = vlr_pago
                                if jrn == '4-':
                                    faturamento = 's'
                                controle_troca = 1
                                jrn_id = self.env['account.journal'].search([
                                    ('name','like', jrn),
                                    ('company_id', '=', session.config_id.company_id.id),
                                    ])[0]
                                for stt in session.statement_ids:
                                    if stt.journal_id.id == jrn_id.id:
                                        pag['statement_id'] = stt.id
                                company_cxt =jrn_id.company_id.id
                                pag['account_id'] = self.env['res.partner'].browse(cod_cli).property_account_receivable_id.id
                                pag['date'] = dt_mov
                                pag['amount'] = vlr_pago
                                pag['journal_id'] = jrn_id.id
                                #pag['journal'] = forma_pgto
                                pag['partner_id'] = cod_cli
                                pag['name'] = ord_name
                                #if controle_troca == 0:
                                if faturamento == 'n':
                                    pag_line.append((0, 0,pag))
                order_line = []
                arq = '%sdet_%s' %(path_arquivos, nome_arq)
                det_arquivo = arq
                desco = desconto_t
                if desconto_t > 0:
                    desconto_t = desconto_t / (total_g+desconto_t)
                with open(arq) as detalhe:
                    dados = json.load(detalhe)
                    num_linha = len(dados)
                    vlr_total = 0.0
                    vlr_totprod = 0.0
                    for item in dados:
                        dado = dados[item]
                        lns = json.loads(dado)
                        linhas = 's'
                        for linha in lns:
                            prd = {}
                            cod_prod = linha['CODPRODUTO']
                            desc = float(linha['VALOR_DESCONTO'].replace(',','.'))
                            qtde = float(linha['QUANTIDADE'].replace(',','.'))
                            preco = float(linha['PRECO'].replace(',','.'))
                            nome = linha['DESCPRODUTO']
                            # se so 1 linha ignora
                            
                            if num_linha == 1:
                               linhas = 'n'
                            soma_t = 0.0
                            total_gx = total_g
                            if linhas == 's': 
                                num_linha -= 1
                            try:
                                prdname = unidecode(nome)
                            except:
                                prdname = 'Nada'
                            vlr_total += (qtde*preco)-desc-desco
                            vlr_totprod = (qtde*preco)-desc-desco
                            # desco vem do pagamento entao zero pra nao descontar novamente
                            desco = 0.0
                            desconto = 0.0
                            if (desc > 0):
                                teve_desconto = 's'
                                desconto = desc / (vlr_totprod+desc)
                            #import pudb;pu.db  
                            if num_linha > 0:
                                desconto = (desconto + desconto_t) * 100
                            else:
                                #desconto Zero, vou editar depois de gravado
                                # pra calcular o desconto correto
                                desconto = 0.0
                                prd = {}
                            #tipo = '1'
                            prd['product_id'] = cod_prod
                            prd['discount'] = desconto
                            prd['qty'] = qtde
                            prd['price_unit'] = preco
                            #prd['tipo_venda'] = tipo
                            prd['name'] = nome
                            prd['price_subtotal'] = vlr_totprod
                            prd['price_subtotal_incl'] = vlr_totprod
                            order_line.append((0, 0,prd))
                            """
                            if troca:
                                trc_prd = self.env['product.template'].search([('name', 'ilike', 'desconto')])
                            prd = {}
                            if trc_prd.id:
                                prd['product_id'] = trc_prd.id
                            else:
                                prd['product_id'] = 2
                                prd['qty'] = 1
                                prd['price_unit'] = troca * (-1)
                                prd['tipo_venda'] = tipo
                                prd['name'] = 'Troca/Devolucao'
                                order_line.append((0, 0,prd))
                            """
                    vals['amount_return'] = vlr_total
                    vals['amount_total'] = vlr_total
                    vals['amount_paid'] = vlr_total
                    vals['lines'] = order_line
                    vals['statement_ids'] = pag_line
                    if teve_desconto == 's':
                        # uso nb_print pra saber q veio do pdv lazarus
                        vals['nb_print'] = 9
                    try:
                        ord_p = pos_ord.create(vals)
                    except:
                        msg_erro += 'ERRO, não integrado pedido : %s<br>' %(prdname)

                    if teve_desconto == 's' and linhas == 's':
                        #ord_p = pos_ord.browse(ords)
                        if (total_g != ord_p.amount_total):
                            tam = len(ord_p.lines)
                            for line in ord_p.lines[tam-1]:
                                x = line.price_unit * line.qty
                                desconto = (ord_p.amount_total-round(total_g,2))/x*100
                                pos_line = self.env['pos.order.line'].browse(ord_p.lines[tam-1].id)
                                pos_line.write({'discount': desconto})
                        # isso coloca como LANCADO
                        #ord_p.action_pos_order_done()
                    if faturamento == 's':
                        # coloquei isto aqui pq qdo tem desconto
                        # e era a prazo o desconto do ultimo item nao ia pra
                        # fatura estas duas linhas abaixo eram feitas no create
                        ord_p.create_order(pag_line, ord_p)
                    else:
                        ord_p.action_pos_order_paid()
                    # exclui arquivo
                    os.remove(mov_arquivo);
                    os.remove(det_arquivo);
                    os.remove(pag_arquivo);
        #print ('Integracao realizada com sucesso.')
        #msg_sis += 'Integracao Finalizada.<br>'
        """
        sqlc = 'SELECT FIRST 3 r.IDCAIXACONTROLE, r.CODCAIXA,  \
               r.VALORABRE, r.VALORFECHA  \
               FROM CAIXA_CONTROLE r WHERE r.VALORFECHA = 1 \
               ORDER BY r.CODCAIXA DESC '
        caixa_fechado = db.query(sqlc)
        for cx in caixa_fechado:
            pos_ses = self.env['pos.session'].search([
                ('id', '=', cx[1]), 
                ('state','=','opened'),
                ('venda_finalizada','=', False)])
            #session = self.env['pos.session'].browse(pos_ses)
            if pos_ses:
                pos_ses.write({'venda_finalizada': True})
                msg_sis = 'CAIXA FECHADO , COM SUCESSO.<br>'
        return msg_sis + '<br>' + msg_erro
        """ 
        return True

class PosConfig(models.Model):
    _inherit = 'pos.config'
    
    ip_terminal = fields.Char(string='ip Terminal Vendas')
    database = fields.Char(string='Banco de Dados')
    
    def action_testar_acesso_terminal(self):
        try:
            db = con.Conexao(self.ip_terminal, self.database)
        except:
            raise UserError(u'Caminho ou nome do banco inválido.')

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _payment_fields(self, ui_paymentline):
        if 'date' in ui_paymentline:
            dt = ui_paymentline['date']
        else:
            dt = ui_paymentline['name']

        return {
            'amount':       ui_paymentline['amount'] or 0.0,
            'payment_date': dt,
            'statement_id': ui_paymentline['statement_id'],
            'payment_name': ui_paymentline.get('note', False),
            'journal':      ui_paymentline['journal_id'],
        }

    @api.model
    def create_order(self, orders, order):
        # Keep only new orders
        order_ids = []
        to_invoice = False
        for stm in orders:
            if stm[2]['journal_id'] in [31,33]:
                to_invoice = True
                continue
            amount = order.amount_total - order.amount_paid
            data = stm[2]
            #if amount != 0.0:
            order.add_payment(data)
            if order.test_paid():
                order.action_pos_order_paid()        
            
        if to_invoice:
            order.action_pos_order_invoice()
            order.invoice_id.sudo().action_invoice_open()
    

    @api.model
    def create(self, values):
        if 'pos_session_id' in values:
            stm_ids = values['statement_ids']
            del values['statement_ids']
            res = super(PosOrder, self).create(values)
            #uso nb_print = 9 qdo importo pdv lazarus
            #if 'nb_print' in values and values['nb_print'] == 9:
            self.create_order(stm_ids, res)
        else:
            res = super(PosOrder, self).create(values)
        return res
