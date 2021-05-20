# -*- coding: utf-8 -*-
from odoo import api, fields, models

from datetime import datetime, date, timedelta
from dateutil import parser
import time
from odoo import SUPERUSER_ID
from ..tools import conexao_chat as conexao
import os
import json
import re
import base64


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, message_type='notification', **kwargs):       
        #PRECISO MARCAR ALGO NAS MSG PRA  SABER QUE FOI DO SUPORTE,
        #CONSEGUINDO ISSO DAI O ARQUIVO DE RETORNO VOLTA SEMPRE
        #COM TODA A CONVERSA PARA O USUARIO,
        #DAI FICA MAIS FACIL O SISTEMA
        # tentando gravar o id do helpdesk em subject da mail_message
        if not 'type' in kwargs:
            cli_id = 0
            for autor in self.channel_partner_ids:
                #import pudb;pu.db
                if autor.customer:
                    cli_id = autor.id
                else:
                    user_id = self.env['res.users'].search([
                        ('partner_id', '=' , autor.id)
                    ]).id
                    user = autor.name
            if cli_id:
                ticket_ids = self.env['helpdesk.ticket'].search([
                   ('partner_id', '=', cli_id),
                   ('user_id', '=', user_id)
                ], limit=1, order='id desc')
                path_integra = '/home/publico/tmp/integra/'
                path_file = '%sretorno_%s.txt' %(path_integra, str(cli_id))
                retorno = {'msg': kwargs['body'],
                    'canal': self.id,
                    'user': user,
                    'atendimento': '00000',
                    'canal': '000',
                    }
                if ticket_ids:
                    retorno['atendimento'] = str(ticket_ids.id)
                    retorno['canal'] = str(self.id)
                    kwargs['subject'] = str(ticket_ids.id)
                    ticket_ids.write({'id_chat_channel': self.id})
                with open(path_file, 'a') as arquivo:
                    arquivo.write(json.dumps(retorno))
                arquivo.close()
        return super(MailChannel, self).message_post(**kwargs)

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    id_chat = fields.Integer(string='Codigo Chat', default=0)
    id_chat_channel = fields.Integer(string='Canal Chat')

    path_integra = '/home/publico/tmp/integra/'
    
    def send_to_channel(self, body, canal, img):
        ch_obj = self.env['mail.channel']
        ch_name =  'geral' #user.name+', '+self.env.user.name
        import pudb;pu.db
        if img:
            #base64.b64decode('b%s' %(img))
            #msg_bytes = img.encode('ascii')
            #base64_bytes = base64.b64encode(msg_bytes)
            #img = base64_bytes.decode('ascii')
            #img = base64.decodestring(json.dumps(img)['image'])
            #img = base64.decodestring(img.ByteData.encode())
            attachment_id = self.env['ir.attachment'].create({
                   'name': 'imagem',
                   'type': 'binary',
                   'datas': img,
                   'datas_fname': 'imagem' + '.jpg',
                   'store_fname': 'imagem_%s.jpg' %(canal),
                   'res_model': self._name,
                   'res_id': self.id,
            })
        import pudb;pu.db
        if canal:
            ch = ch_obj.sudo().search([('id', '=', canal)])
            for autor in ch.channel_partner_ids:
                if autor.customer:
                    autor_id = autor.id
            if img:
                post_vars = {'author_id': autor_id, 
                    'subject': "Message subject", 
                    'body': body, 
                    'partner_ids': ch.channel_partner_ids, 
                    'attachment_ids': [attachment_id.id]}
            else:
                post_vars = {'author_id': autor_id, 'subject': "Message subject", 'body': body, 'partner_ids': ch.channel_partner_ids,}
            ch.message_post(type="notification", subtype="mt_comment", **post_vars)
        return True

    @api.model
    def cron_helpdesk_integra(self):
        # ---------------------------------------------------------------------------
        # este cron esta sendo chamado pelo flask
        # ---------------------------------------------------------------------------
        # VERIFICO SE EXISTE ALGUM PEDIDO NOVO DE SUPORTE
        #import pudb;pu.db
        for arq in os.listdir(self.path_integra):                
            if arq[:7] == 'retorno':
                continue
            excluir_arquivo = 'N'
            with open(self.path_integra + arq) as arquivo:
                x = 1
                for linha in arquivo:
                    if 'partner_ids' in linha:
                        continue
                    dados = json.loads(linha)
                    arq_contato = arq[len(arq)-7:len(arq)]
                    # pego os tickets Novos ou em Andamento
                    cnpj = dados['cnpj']
                    cnpj =  '%s.%s.%s/%s-%s' %(cnpj[:2],
                            cnpj[2:5],cnpj[5:8],
                            cnpj[8:12],cnpj[12:14])
                    cli = self.env['res.partner'].search([('cnpj_cpf','=', cnpj)])
                    ticket_ids = self.search([('stage_id', 'in', [1,2]), 
                        ('partner_id', '=', cli.id),
                    ])
                    # NAO EXISTE ADICIONANDO
                    #import pudb;pu.db
                    if not ticket_ids:
                        vals = {}
                        vals['id_chat'] = dados['cliente']
                        vals['name'] = dados['title']
                        vals['description'] = dados['chat']
                        vals['user_id'] = 0
                        vals['partner_id'] = cli.id
                        ticket_ids = super().create(vals)
                        ticket_ids._onchange_partner_id()
                    #import pudb;pu.db
                    if arq_contato == '001.txt' and ticket_ids.stage_id.id == 1:
                        # Arquivo 1 esta aqui entao enviar MSG Geral
                        chat = '%s - (%s) %s - %s' %(
                            ticket_ids.number,
                            dados['cliente'], 
                            dados['empresa'], 
                            dados['chat'])
                        usuarios = self.env['res.users'].search([
                            ('login', 'ilike', 'atsti')
                        ])
                        #import pudb;pu.db
                        for user in usuarios:
                            #self.env.user.notify_info(message=chat)
                            user.notify_info(message=chat)
                        
                    if arq_contato != '001.txt':
                        #import pudb;pu.db
                        # retorno do usuario
                        if 'canal' in dados:
                            canal = dados['canal']
                            import pudb;pu.db
                            #img = base64.decodestring(json.dumps(dados)['img'])
                            img = base64.decodebytes(dados['img'])
                            self.send_to_channel(dados['chat'], canal, img)
                            ticket_ids.write({'id_chat_channel': canal})
                            excluir_arquivo = 'S'
            arquivo.close()
            # exclui o arquivo se ja registrou a msg        
            if excluir_arquivo == 'S':
                os.unlink(self.path_integra + arq)
        return True

    """
    @api.model
    def cron_helpdesk_integra_segundos(self):
            # alterar o cron para 20 segundos
            #import pudb;pu.db
            cron = self.env['ir.cron'].browse([38])
            cron_seg = self.env['ir.cron'].browse([39])
            proxima = cron_seg.nextcall + timedelta(seconds=20)
            cron.write({'nextcall': proxima})
    """

    @api.multi
    def write(self, vals):
        for ticket in self:
            #import pudb;pu.db
            if vals.get('stage_id') and vals['stage_id'] == 2:
                if not ticket.user_id:
                    vals['user_id'] = self.env.user.id
                path_file = '%schat_%s_001.txt' %(self.path_integra, str(self.partner_id.id))
                if os.path.exists(path_file):
                    os.unlink(path_file)
            if vals.get('user_id'):
                now = fields.Datetime.now()
                vals['assigned_date'] = now
            if vals.get('stage_id') and vals['stage_id'] == 4:
                ch_obj = self.env['mail.message']
                ch = ch_obj.sudo().search([
                    ('res_id', '=', self.id_chat_channel),
                    ('author_id', 'in', [self.user_id.partner_id.id, self.partner_id.id]),
                ], limit=30)
                desc = ''
                for msg in ch:
                    dta = msg.date
                    dta = ('%s/%s/%s %s:%s:%s') %(
                        str(dta.day).zfill(2),
                        str(dta.month).zfill(2),
                        str(dta.year),
                        str(dta.hour).zfill(2),
                        str(dta.minute).zfill(2),
                        str(dta.second).zfill(2),
                        )
                    desc += dta + ': ' + msg.body
                vals['description'] = desc
                

        res = super(HelpdeskTicket, self).write(vals)
