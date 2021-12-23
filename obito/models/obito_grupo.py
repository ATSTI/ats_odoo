# © 2021 Carlos R. Silveira, Manoel dos Santos, ATSti Solucoes
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from datetime import datetime, timedelta


class ObitoGrupo(models.Model):
    _name = "obito.grupo" 
    _description = "Cadastro dos grupos"
    
    name = fields.Char('Nome Do Grupo', size=40)
    codigo = fields.Char('Código', size=1)
    inscricao = fields.Integer('Inscrição')
    faixa = fields.Boolean('Faixa ?')
    insc_ini = fields.Integer('Faixa')
    insc_fim = fields.Integer('a')