##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class ResCompanyInterest(models.Model):

    _name = 'res.company.interest'
    _description = 'Account Interest'

    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        ondelete='cascade',
    )
    receivable_account_ids = fields.Many2many(
        'account.account',
        string='Conta a Receber',
        help='Conta de lançamento do Contas a Receber',
        required=True,
        domain="[('user_type_id.type', '=', 'receivable'),"
        "('company_id', '=', company_id)]",
    )
    invoice_receivable_account_id = fields.Many2one(
        'account.account',
        string='Conta de Recebimento',
        help='Se não informada, será usada a conta do cadastro.',
        domain="[('user_type_id.type', '=', 'receivable'),"
        "('company_id', '=', company_id)]",
    )
    interest_product_id = fields.Many2one(
        'product.product',
        'Produto/Item para Lançar',
        required=True,
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        'Conta Analitica',
    )
    rate = fields.Float(
        'Juros (% dia)',
        required=True,
        digits=(7, 4)
    )
    multa = fields.Float(
        'Multa',
        digits=(7, 4)
    )

    automatic_validation = fields.Boolean(
        'Validar automaticamente?',
        help='Validar a fatura automaticamente, ou deixar como provisória?',
        default=True,
    )
    rule_type = fields.Selection([
        ('daily', 'Dia(s)'),
        ('weekly', 'Semana(s)'),
        ('monthly', 'Mês(s)'),
        ('yearly', 'Ano(s)'),
    ],
        'Recorrência',
        help="Repetir a atualização do juros/multa com que frequência",
        default='monthly',
    )
    interval = fields.Integer(
        'Repetir cada',
        default=1,
        help="Repetir a cada (Dia/Semana/Mês/Ano)"
    )
    tolerance_interval = fields.Integer(
        'Tolerância',
        default=1,
        help="Numero de dias para tolerância da cobrança dos juros/multa. 0 = não tolerância"
    )
    next_date = fields.Date(
        'Data da próxima atualização',
        default=fields.Date.today,
    )
    domain = fields.Char(
        'Filtro adicional',
        default="[]",
        help="Adicionar filtro para uma atualização especifica."
    )
    has_domain = fields.Boolean(compute="_compute_has_domain")

    @api.model
    def _cron_recurring_interests_invoices(self):
        _logger.info('Running Interest Invoices Cron Job')
        # NAO TA RODANDO CONFERE A DATA NO CAMPO EMPRESA SE E MENOR
        current_date = fields.Date.today()       
        self.search([('next_date', '<=', current_date)]
                    ).create_interest_invoices()

    @api.multi
    def create_interest_invoices(self):
        for rec in self:
            _logger.info(
                'Creating Interest Invoices (id: %s, company: %s)', rec.id,
                rec.company_id.name)
            interests_date = rec.next_date

            rule_type = rec.rule_type
            interval = rec.interval
            tolerance_interval = rec.tolerance_interval
            # next_date = fields.Date.from_string(interests_date)
            if rule_type == 'daily':
                next_delta = relativedelta(days=+interval)
                tolerance_delta = relativedelta(days=+tolerance_interval)
            elif rule_type == 'weekly':
                next_delta = relativedelta(weeks=+interval)
                tolerance_delta = relativedelta(weeks=+tolerance_interval)
            elif rule_type == 'monthly':
                next_delta = relativedelta(months=+interval)
                tolerance_delta = relativedelta(months=+tolerance_interval)
            else:
                next_delta = relativedelta(years=+interval)
                tolerance_delta = relativedelta(years=+tolerance_interval)
            interests_date_date = fields.Date.from_string(interests_date)
            # buscamos solo facturas que vencieron
            # antes de hoy menos un periodo
            # TODO ver si queremos que tambien se calcule interes proporcional
            # para lo que vencio en este ultimo periodo
            to_date = fields.Date.to_string(
                interests_date_date - tolerance_delta)

            rec.create_invoices(to_date)

            # seteamos proxima corrida en hoy mas un periodo
            rec.next_date = fields.Date.to_string(
                interests_date_date + next_delta)

    @api.multi
    def create_invoices(self, to_date):
        self.ensure_one()
        lang_code = self.env.context.get('lang', self.env.user.lang)
        lang = self.env['res.lang']._lang_get(lang_code)
        date_format = lang.date_format
        to_date_format = fields.Date.from_string(
            to_date).strftime(date_format)

        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id)], limit=1)
        
        # TODO se usa boleto, nao da pra cancelar a fatura
        #
        #('boleto', '=', False),
        #import pudb;pu.db
        invoice_domain = [
            ('account_id', 'in', self.receivable_account_ids.ids),
            ('state', '=', 'open'),
            ('date_due', '<', to_date),
            ('product_document_id', '=', False),
        ]
        invoice = self.env['account.invoice']
        invoice_ids = invoice.search(invoice_domain)
        #import pudb;pu.db
        total_items = len(invoice_ids)
        _logger.info('%s interest invoices will be generated', total_items)
        idx = 0
        for line in invoice_ids:
            debt = line.residual
            if not debt or debt <= 0.0:
                continue
            _logger.info(
                'Creating Interest Invoice (%s of %s) with values:\n%s',
                idx + 1, total_items, line)
            idx += 1
            partner_id = line.partner_id.id
            # cancelo a FATURA : 
            line.action_invoice_cancel()
            #line.action_invoice_draft() # Nao funciona, por isso o write abaixo
            if line.filtered(lambda inv: inv.state != 'cancel'):
                raise UserError(_("Invoice must be cancelled in order to reset it to draft."))
            # go from canceled state to draft state
            line.write({'state': 'draft', 'date': False})
            inv_line = self._prepare_interest_invoice_line(
                    line, debt, to_date_format)
            if inv_line:
                line.invoice_line_ids.create(#
                    inv_line)
            iml = line.invoice_line_move_line_get()
            company_currency = line.company_id.currency_id
            total, total_currency, iml = line.compute_invoice_totals(company_currency, iml)
            line.residual = total
            # update amounts for new invoice
            line.compute_taxes()
            
            if self.automatic_validation:
                try:
                    x = line.residual
                    line.action_invoice_open()
                except Exception as e:
                    _logger.error(
                        "Something went wrong "
                        "creating interests invoice: {}".format(e))

    @api.multi
    def prepare_info(self, to_date_format, debt):
        self.ensure_one()

        res = _(
            'Deuda Vencida al %s: %s\n'
            'Tasa de interés: %s') % (
                to_date_format, debt, self.rate)

        return res

    @api.multi
    def _prepare_interest_invoice_line(self, invoice, debt, to_date):
        self.ensure_one()
        amount = 0.0
        company = self.company_id
        current_date = fields.Date.today()
        quantidade_dias = abs((current_date - invoice.date_due).days)-self.tolerance_interval
        import pudb;pu.db
        for inv_line in invoice.invoice_line_ids:
            if inv_line.product_id.id != self.interest_product_id.id:
                amount += inv_line.price_unit
        if self.multa:
            multa = amount * (self.multa/100)
        amount = company.currency_id.round(
            ((self.rate/100) * quantidade_dias * amount)+multa)
        for inv_line in invoice.invoice_line_ids:
            if inv_line.product_id.id == self.interest_product_id.id:
                inv_line.write({'price_unit': amount})
                return False
        line_data = self.env['account.invoice.line'].with_context(
            force_company=company.id).new(dict(
                product_id=self.interest_product_id.id,
                quantity=1.0,
                invoice_id=invoice.id,
                account_id = self.interest_product_id.categ_id.property_account_income_categ_id.id
            ))
        line_data._onchange_product_id()
        line_data['icms_aliquota_credito'] = 0.0
        line_data['icms_st_aliquota_deducao'] = 0.0
        line_data['cofins_aliquota'] = 0.0
        line_data['icms_substituto'] = 0.0
        line_data['icms_bc_st_retido'] = 0.0
        line_data['icms_aliquota_st_retido'] = 0.0
        line_data['icms_st_retido'] = 0.0
        line_data['price_unit'] = amount
        line_data['account_analytic_id'] = self.analytic_account_id.id
        line_data['name'] = line_data.product_id.name
        line_values = line_data._convert_to_write(
            {field: line_data[field] for field in line_data._cache})
        return line_values

    @api.depends('domain')
    def _compute_has_domain(self):
        self.has_domain = len(safe_eval(self.domain)) > 0
