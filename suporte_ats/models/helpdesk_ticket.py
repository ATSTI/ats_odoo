# -*- coding: utf-8 -*-
from odoo import api, fields, models

from datetime import datetime, date, timedelta
from dateutil import parser
import time
from odoo import SUPERUSER_ID
from ..tools import conexao_chat as conexao
import re


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    id_chat = fields.Integer(string='Codigo Chat', default=0)
    id_chat_last = fields.Integer(string='Codigo Chat Final')

    def send_to_channel(self, body):
        #users = result.user_id
        ch_obj = self.env['mail.channel']
        #body = body +' '+ result.seq_no
        ch_name =  'geral' #user.name+', '+self.env.user.name
        ch = ch_obj.sudo().search([('name', 'ilike', str(ch_name))])
        for user in ch.channel_last_seen_partner_ids:
            ch.message_post(attachment_ids=[],body=body,content_subtype='html',
                  message_type='comment',partner_ids=[],subtype='mail.mt_comment',
                  email_from=user.partner_id.email,author_id=user.partner_id.id)
        #self.env.user.notify_default(message=ch_name)
        #user.notify_default(message=ch_name)
        return True

    @api.model
    def cron_helpdesk_integra(self):
        # pego os tickets Novos ou em Andamento
        ticket_ids = self.search([('stage_id', 'in', [1,2]),          
            ('id_chat', '>', 0)])
        atendendo = []
        con = conexao.Conexao()
        for tk in ticket_ids:
            cnpj = ''
            if tk.partner_id and tk.partner_id.cnpj_cpf:
                cnpj = re.sub('[^0-9]', '', tk.partner_id.cnpj_cpf)
            else:
                continue # sem cliente nao da pra fazer nada
            # cria uma lista dos clientes q estamos atendendo
            atendendo.append(cnpj)
            # leio o bd do chat
            nova_msg = con.busca_nova_msg(cnpj, tk.id_chat, tk.id_chat_last)
            for msg in nova_msg:
                dsc = tk.description + ' <br />' +  msg.descricao
                if '#fim' in msg.descricao:
                    tk.write({'description': dsc, 'stage_id': 4, 'id_chat_last': msg.id})
                else:
                    tk.write({'description': dsc, 'id_chat_last': msg.id})
        # vendo se tem Suporte novo
        suporte_novo = con.busca_novo_suporte(atendendo)
        msg_id = 0
        for msg in suporte_novo:
            if msg_id > 0 and msg_id >= msg.id:
                continue
            #import pudb;pu.db
            # Suporte novo
            x = msg.cliente
            #tkt = self.env['helpdesk.ticket']
            cnpj = ''
            if len(msg.cliente) == 14:
                cnpj =  '%s.%s.%s/%s-%s' %(msg.cliente[:2],
                    msg.cliente[2:5],msg.cliente[5:8],
                    msg.cliente[8:12],msg.cliente[12:14])
            vals = {}
            cli = 0
            if cnpj:
                cli = self.env['res.partner'].search([('cnpj_cpf','=', cnpj)])
                if cli:
                    vals['partner_id'] = cli.id

            vals['id_chat'] = msg.id
            vals['name'] = msg.suporte
            vals['description'] = msg.descricao
            vals['user_id'] = 0
            data_atual = date.today()
            hoje = '%s-%s-%s 03:00:00' %(str(data_atual.year),
                str(data_atual.month).zfill(2),
                str(data_atual.day).zfill(2))
            #import pudb;pu.db
            ticket_ids = self.search([
                    ('stage_id', '=', 4),
                    ('partner_id', '=', cli.id),
                    ('id_chat', '=', msg.id),
                    ('create_date', '>', hoje)
                ])
            if ticket_ids:
                msg_id = ticket_ids.id_chat_last
                continue
            suporte_msg = '%s-%s' %(msg.suporte, cli.name)
            ticket_ids = self.search([
                    ('stage_id', 'in', [1,2]),
                    ('partner_id', '=', cli.id),
                    ('id_chat', '=', msg.id),
                    ('id_chat_last', '<', msg.id),
                    ('name', '=', msg.suporte),
                    ('create_date', '>', hoje)
                ])
            
            for tk in ticket_ids:
                dsc = tk.description + ' <br />' +  msg.descricao
                if '#fim' in msg.descricao:
                    tk.write({'description': dsc, 'stage_id': 4})
                else:
                    tk.write({'description': dsc})
                continue
            if not ticket_ids:
                self.send_to_channel(suporte_msg)
                super().create(vals)
        return True
