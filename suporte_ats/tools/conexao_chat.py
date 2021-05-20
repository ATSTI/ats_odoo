# -*- coding: utf-8 -*-
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import date

Base = declarative_base()
 
class Suporte(Base):
    # Base Sqlitle do Chat
    __tablename__ = 'suporte'
    
    id = Column(Integer, primary_key=True,  autoincrement=True)
    cliente = Column(String(20), nullable=False)
    contato = Column(String(60), nullable=False)
    data_suporte = Column(DateTime(timezone=True), default=func.now())
    suporte = Column(String(60), nullable=False)
    descricao = Column(String(120), nullable=False)
    situacao = Column(String(20), default='nova')


class Conexao(object):
    
    def inicia_bd(self):
        engine = create_engine('sqlite:////home/publico/desenv/python/suporte.db')
        #Base.metadata.drop_all(engine) # usado pra excluir BD e criar novamente.
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        return session

    """    
    def grava_conversa(self, cliente, contato, data_suporte, suporte, descricao):
        conversa = Suporte(cliente=cliente, contato=contato, 
            suporte=suporte, descricao=descricao)
        ses = self.inicia_bd()
        ses.add(conversa)
        ses.commit()
    """
        
    def busca_conversa(self, cliente, contato):
        ses = self.inicia_bd()
        #import pudb;pu.db
        conversa = (
            ses.query(Suporte)
            .filter(Suporte.cliente == cliente, 
                Suporte.contato == contato
            )
        )
        for cnv in conversa:
            return conversa
        return 'NADA'

    def busca_nova_msg(self, cliente, id_reg, id_chat_final):
        ses = self.inicia_bd()
        #import pudb;pu.db
        conversa = (
            ses.query(Suporte)
            .filter(Suporte.cliente == cliente, 
                Suporte.id > id_reg,
                Suporte.id > id_chat_final
            )
        )
        for cnv in conversa:
            return conversa
        return []

    def busca_novo_suporte(self, clientes_atendendo):
        #import pudb;pu.db
        ses = self.inicia_bd()
        #result = session.query(Customers).filter(Customers.id.in_([1,3]))
        # notin_([42, 43, 44, 45])
        data_atual = date.today()
        hoje = '%s-%s-%s 03:00:00' %(str(data_atual.year),
            str(data_atual.month).zfill(2),
            str(data_atual.day).zfill(2))
        conversa = []
        if len(clientes_atendendo):
            conversa = (
                ses.query(Suporte)
                    .filter(
                        Suporte.cliente.notin_(clientes_atendendo),
                        Suporte.data_suporte>hoje
                )
            )
        else:
           conversa = (
                ses.query(Suporte)
                    .filter(
                        Suporte.data_suporte>hoje
                )
            )
        for cnv in conversa:
            return conversa
        return []

