from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.sql import insert
from sqlalchemy.exc import SQLAlchemyError
#import fdb
from flask import jsonify
from skpy import Skype
import json
import datetime
from atsadmin.tabelas_ats import Cliente
from atsadmin.conexao_firebird import AtsConn
import os.path
import re
from odoo_rpc_client import Client

class AlchemyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data) # this will fail on non-encodable values, like other classes
                    fields[field] = data
                except TypeError:
                    #import pudb;pu.db
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)

class AtsCliente:
    _name = 'ats.cliente'
    _description = "Cadastro Clientes"
    
    #path_integra = '/opt/odoo/integra/'
    path_integra = '/home/publico/tmp/integra/'

    def __init__(self):
        #import pudb;pu.db
        #con = AtsConn.sessao()
        #for cli in con.query(Cliente).order_by(Cliente.codcliente):
        #    print('Cliente : %s' %(cli.nomecliente))
        self.envia_msg_odoo()
        return None

    def envia_msg_odoo(self):
        #import pudb;pu.db
        server = Client('192.168.6.100', '21_admin', 'carlos@atsti.com.br', 'a2t00s7')
        #server.user
        #print(server.user.name)
        help_obj = server['helpdesk.ticket']
        help_obj.cron_helpdesk_integra()

    def retorno_suporte(self, suporte):
        #linha  = json.loads(suporte)
        #self.envia_msg_odoo()
        linha = suporte
        arquivo = ''
        id_atende = str(linha['id']).zfill(3)
        # Ve se alguem respondeu pra ATENDER
       # se tem algum arquivo de retorno
        path_file = '%sretorno_%s.txt' %(self.path_integra, linha['cliente'])
        dados = {'msg': '', 'user': '', 'atendimento': '00000', 'canal': '000'}
        #import pudb;pu.db
        if os.path.exists(path_file):
            with open(path_file) as arquivo:
                try:
                    dados = json.load(arquivo)
                except:
                    dados = ''
            os.unlink(path_file)
        return jsonify(dados)

    def cliente_suporte(self, suporte):
        #import pudb;pu.db
        #linha  = json.loads(suporte)
        linha = suporte
        arquivo = ''
        id_atende = str(linha['id']).zfill(3)
        path_file = '%schat_%s_%s.txt' %(self.path_integra, linha['cliente'], id_atende)
        if os.path.exists(path_file):
            with open(path_file, 'w') as arquivo:
               # x = 1
               #for dia in arquivo:
               #     dados = dia.replace('\n', '')
               arquivo.write(json.dumps(linha))
            arquivo.close
        else:
            with open(path_file, 'w') as f:
                f.write(json.dumps(linha))
            f.close
        dados = {'user': '' , 
                'msg': '',
                'atendimento': '0000', 'canal': '000'
            }
        
        if (linha['id'] == '1'):
            # MENSAGEM PADRAO
            dados = {'user': 'ATS Suporte' , 
                'msg': 'Aguarde um momento por favor...',
                'atendimento': '0000', 'canal': '000'
            }
            skype_obj = Skype('ats@atsti.com.br','a2t00s11')
            channel = skype_obj.chats.chat('19:66cb162407b442c49ef66303ed394e23@thread.skype')
            channel.sendMsg('%s - %s' %(linha['empresa'], linha['chat']))
        else:
            # Ve se alguem respondeu pra ATENDER
             # se tem algum arquivo de retorno
            path_file = '%sretorno_%s.txt' %(self.path_integra, linha['cliente'])
            if os.path.exists(path_file):
                with open(path_file) as arquivo:
                    dados = json.load(arquivo)
        return jsonify(dados)

    def integra_produto(self, empresa):
        dados = []
        path_file = self.path_integra + empresa + '/produto.txt'
        if os.path.exists(path_file):
            with open(path_file) as json_file:
                dados = json.load(json_file)
        else:
            prod = {}
            prod['codproduto'] = 0
            dados.append(prod)
        return jsonify(dados)

    def integra_usuario(self, empresa):
        dados = []
        path_file = self.path_integra + empresa + '/usuario.txt'
        if os.path.exists(path_file):
            with open(path_file) as json_file:
                dados = json.load(json_file)
        else:
            user = {}
            user['codusuario'] = 0
            dados.append(user)
        return jsonify(dados)

    def integra_caixa(self, empresa):
        path_file = self.path_integra + empresa + '/caixa.txt'
        dados = []
        #import pudb;pu.db
        if os.path.exists(path_file):
            with open(path_file) as json_file:
                dados = json.load(json_file)
        else:
            caixa = {}
            caixa['codcaixa'] = 0
            dados.append(caixa)
        x = 'N'
        if dados:
            x = jsonify(dados)
        return x

    def integra_cli(self, empresa):
        path_file = self.path_integra + empresa + '/cliente.txt'
        dados = []
        #import pudb;pu.db
        if os.path.exists(path_file):
            with open(path_file) as json_file:
                dados = json.load(json_file)
        else:
            cliente = {}
            cliente['codcliente'] = 0
            dados.append(cliente)
        return jsonify(dados)

    def integra_sangria(self, dados, empresa):
        path_file = self.path_integra + empresa + '/caixa_mov.txt'
        dados_json = json.loads(dados)
        arquivo = ''
        for item in dados_json:
            with open(path_file, 'w') as f:
                f.write(json.dumps(dados_json))
                f.close
            ver_json = json.loads(dados_json[item])
            for mov in ver_json:
                arquivo = 'caixa_mov_%s.txt' %(mov.get('CAIXA'))
        return arquivo

    def integra_venda(self, dados, empresa):
        path_file = self.path_integra + empresa + '/'
        dados_json = json.loads(dados)
        feito = 'N'
        for item in dados_json:
            if 'pag' in item:
                x = dados_json[item]
                ver_json = json.loads(x)
                for det in ver_json:
                    codmov = det.get('CODMOVIMENTO')
                    arquivo = '%spag_%s.txt' %(path_file,codmov)
                    with open(arquivo, 'w') as f:
                        f.write(json.dumps(dados_json))
                        f.close
                        feito = 'pag_%s' %(codmov)
                    break
                break
            if 'CODCLIENTE' in dados_json:
                codmov = dados_json['CODMOVIMENTO']
                arquivo = '%smov_%s.txt' %(path_file,codmov)
                with open(arquivo, 'w') as f:
                        f.write(json.dumps(dados_json))
                        f.close
                        feito = 'mov_%s' %(codmov)
                break
            if 'item' in item:
                x = dados_json[item]
                ver_json = json.loads(x)
                for det in ver_json:
                    codmov = det.get('CODMOVIMENTO')
                    arquivo = '%sdet_%s.txt' %(path_file,codmov)
                    #data_file = open(arquivo, 'w')
                    with open(arquivo, 'w') as f:
                        f.write(json.dumps(dados_json))
                        f.close
                        feito = 'det_%s' %(codmov)
                    break
            break
            #z = json.dumps(item)
            #d = json.loads(z)
            
            #print (x)
        return feito

    def ver_cliente(self):
        lista = []
        lista.append('Server Apache 3.5')
        return jsonify(lista)

    def cliente_insert(self, dados):
        con = AtsConn.sessao()
        #Cliente.insert().values(dados)
        try:
            i = insert(Cliente)
            i = i.values(dados)
            con.execute(i)
            con.commit()
            con.close_all()
        except SQLAlchemyError as e:
            error = str(e.__dict__['orig'])
            con.close_all()
            return error
        return 'Cadastro incluido com sucesso.'

    def cliente_update(self, dados):
        #import pudb;pu.db
        con = AtsConn.sessao()
        # Convert Models to dicts
        #entry_dict = dados.as_dict()
        #db_result_dict = cli_ids.first().as_dict()

        # Update database result with passed in entry. Skip of None
        #for value in dados:
        #    if dados[value] is not None:
        #        cli_ids = dados[value]

        # Update db and close connections
        #cli_ids.update(dados)
        cli = con.query(Cliente).filter_by(codcliente=dados['codcliente'])
        #update_statement = Cliente.update()\
        #   .where(codcliente = dados['codcliente'])\
        #   .values(atualiza)
        try:
            cli.update(dados)
            con.commit()
            con.close_all()
        except:
            con.close_all()
            return 'ERRO na atualização do cadastro.'
        return 'Cadastro atualizado com sucesso.'

    def cliente_tabela(self):
        # LEIO A TABELA INTEIR E CRIO UM JSON COM OS CAMPOS
        tabela = []
        for cli in Cliente.__table__.columns:
            campos = {}
            campos['campo'] = cli.name
            campos['tipo'] = str(cli.type)
            campos['tam'] = '0'
            if str(cli.type) not in ('INTEGER', 'SMALLINT', 'FLOAT', 'DATE', 'DATETIME'):
                campos['tam'] = str(cli.type.length)
            tabela.append(campos)
        #import pudb;pu.db
        return jsonify(tabela)

    def estrutura_filtro(self):
        # VOU CRIAR UM JSON SOMENTE CAMPOS PRA EXIBIR GRID
        tabela = []
        campos = {
            'campo': 'codcliente',
            'titulo': 'Código',
            'tipo': 'INTEGER',
            'tam': '70',
            }
        tabela.append(campos)
        campos = {
            'campo': 'nomecliente',
            'titulo': 'Nome',
            'tipo': 'VARCHAR',
            'tam': '400',
            }
        tabela.append(campos)
        campos = {
            'campo': 'razaosocial',
            'titulo': 'Razão Social',
            'tipo': 'VARCHAR',
            'tam': '300',
            }
        tabela.append(campos)
        campos = {
            'campo': 'cnpj',
            'titulo': 'CNPJ/CPF',
            'tipo': 'VARCHAR',
            'tam': '80',
            }
        tabela.append(campos)
        return jsonify(tabela)

    def consulta_cliente(self, codcliente=None, outros=None):
        con = AtsConn.sessao()
        lista = []
        #for cli in Cliente.__table__.columns:
        #    campos = {}
        #    campos['campo'] = cli.name
        #    tabela.append(campos)

        cli_ids = con.query(Cliente).filter(
            Cliente.codcliente==int(codcliente['codcliente'])).first()
        cli_dict = dict((col, getattr(cli_ids, col)) for col in cli_ids.__table__.columns.keys())
        linha = {}
        for value in cli_dict:
            # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
            # TODO tratar campos DATA, e campos Relacionados
            linha[value] = cli_dict[value]
        #import pudb;pu.db
        lista.append(linha)
        return jsonify(lista)
