from flask import Flask
from flask import request        
from atsadmin.ats_cliente import AtsCliente


app = Flask(__name__)

@app.route('/chat', methods=['GET', 'POST'])
def suporte_chat():
    if request.method == 'POST':
        #import pudb;pu.db
        data = request.json
        if 'suporte' in data:
            cli = AtsCliente()
            x = cli.cliente_suporte(data['suporte'])
        return x
    else:
        return 'ATS Ti Soluções - Suporte'

@app.route('/', methods=['GET', 'POST'])
def hello_world():
    if request.method == 'POST':
        #import pudb;pu.db
        data = request.json
        if 'dados' in data:
            cli = AtsCliente()
            x = cli.edita_cliente(data['dados'])
        if 'cliente_tabela' in data:
            cli = AtsCliente()
            x = cli.cliente_tabela()
            #import pudb;pu.db
        if 'cliente_filtro' in data:
            cli = AtsCliente()
            x = cli.cliente_filtro()
            #import pudb;pu.db
        if 'cliente' in data:
            cli = AtsCliente()
            x = cli.consulta_cliente(data['cliente'])
        if 'cliente_update' in data:
            cli = AtsCliente()
            x = cli.cliente_update(data['cliente_update'])
        if 'cliente_insert' in data:
            cli = AtsCliente()
            x = cli.cliente_insert(data['cliente_insert'])
        if 'tab_venda' in data:
            cli = AtsCliente()
            x = cli.integra_venda(data['tab_venda'], data['body'])
        if 'tab_cli' in data:
            cli = AtsCliente()
            x = cli.integra_cli(data['body'])
        if 'tab_caixa' in data:
            cli = AtsCliente()
            x = cli.integra_caixa(data['body'])
        if 'tab_usuario' in data:
            cli = AtsCliente()
            x = cli.integra_usuario(data['body'])
        if 'tab_produto' in data:
            cli = AtsCliente()
            x = cli.integra_produto(data['body'])
        if 'tab_sangria' in data:
            cli = AtsCliente()
            #x = cli.integra_sangria(data['body'])
            x = cli.integra_sangria(data['tab_sangria'], data['body'])
        if 'cnpj' in data:
            cli = AtsCliente()
            x = cli.cliente_cnpj(data['cnpj'])

        return x
    else:
        #import pudb;pu.db
        cli = AtsCliente()
        z = cli.ver_cliente()
        return z

if __name__ == "__main__":
    app.run('0.0.0.0', port=8905, debug=False)
#if __name__ == "__main__":
#    app.run(host='0.0.0.0')
