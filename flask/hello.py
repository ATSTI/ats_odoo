from flask import Flask
from flask import request        
from atsadmin.ats_cliente import AtsCliente


app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def hello_world():
    #import pudb;pu.db
    if request.method == 'POST':
        # file1 = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        #if file1.filename != '':
        #   x = 'a'
        data = request.json
        if 'chat' in data:
            # leio o que tem no chat e gravo em um arquivo
            cli = AtsCliente()
            x = cli.cliente_suporte(data)
        if 'chat_retorno' in data:
            # leio o que tem no chat e gravo em um arquivo
            cli = AtsCliente()
            x = cli.retorno_suporte(data)
            
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
        if 'cliente' in data and not 'chat' in data and not 'chat_retorno' in data:
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
            
        return x
    else:
        #import pudb;pu.db
        cli = AtsCliente()
        #z = cli.ver_cliente()
        chat = cli.retorno_suporte()
        return chat

if __name__ == "__main__":
    app.run('0.0.0.0', port=8905, debug=False)
