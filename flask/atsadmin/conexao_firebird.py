from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import fdb


class AtsConn:
    _name = 'ats.conn'
    _description = "Conexao Database"
    
    #def __init__(self):
    #    #return session

    def sessao():
        #import pudb;pu.db
        database_driver='firebird+fdb'
        database='//sysdba:masterkey@localhost:3050///home/publico/bd/ats_3.fdb?charset=utf8'
        encoding='UTF8'
        conncection = ':'.join([database_driver, database])
        engine = create_engine(conncection, encoding=encoding)
        Session = sessionmaker(bind=engine)
        return Session()
        

"""
for cli in session.query(Cliente).order_by(Cliente.codcliente):
    print('Cliente : %s' %(cli.nomecliente))

import pudb;pu.db
query = session.query(Cliente).filter_by(nomecliente='Adriano Marcelino da Silva')
query.count()

session.query(Cliente).filter(Cliente.nomecliente.like('%Carolina%')).first()
query.count()
"""
