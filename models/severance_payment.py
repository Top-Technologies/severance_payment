from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class SeverancePayment(models.Model):
    _name = 'severance.payment'
    _description = 'Severance Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    monthly_salary = fields.Monetary(compute="compute_monthly_salary",store=True, string='Monthly Salary', readonly=True, currency_field='company_currency_id')
    annual_salary = fields.Monetary(string='The payment should not be more than', compute='_compute_annual_salary', store=True, currency_field='company_currency_id')
    exchange_rate=fields.Float(string="Exchange Rate")
    years_worked = fields.Integer(string='Years Worked', compute='_compute_years_worked', store=True)
    months_worked = fields.Integer(string='Months Worked', compute='_compute_years_worked', store=True)
    days_worked = fields.Integer(string='Days Worked', compute='_compute_years_worked', store=True)
    payout_amount = fields.Monetary(string='Gross Severance Payment', compute='_compute_payout_amount', store=True, currency_field='company_currency_id')
    payout_ratio = fields.Float(string='Tax Rate', compute='_compute_payout_ratio', store=True, digits=(10, 2))
    adjusted_payout = fields.Monetary(string='Before Decimal Tax Amount', compute='_compute_adjusted_payout', store=True, currency_field='company_currency_id')
    adjusted_payout_after_dot = fields.Monetary(string='After Decimal Tax Amount', compute='_compute_adjusted_payout_after_dot', store=True, currency_field='company_currency_id')
    total_adjusted_payout = fields.Monetary(string='Total Tax Amount', compute='_compute_total_adjusted_payout', store=True, currency_field='company_currency_id')
    total_payment = fields.Monetary(string='Net Payment', compute='_compute_total_payment', store=True, currency_field='company_currency_id')
    contract_start_date = fields.Date(string='Contract Start Date', related='employee_id.contract_id.date_start', readonly=True)
    contract_end_date = fields.Date(string='Contract End Date', related='employee_id.contract_id.date_end', readonly=True)
    company_currency_id = fields.Many2one('res.currency', related='employee_id.company_id.currency_id', readonly=True, string="Currency")
    payment_date = fields.Date(string="Payment Date")
    approved_by = fields.Many2one('res.users', string="Submitted By")
    validated_by = fields.Many2one('res.users', string="Validated by")
    currency_id = fields.Many2one('res.currency', string="Currency")
    reason = fields.Char(string="Reason")

    department_id = fields.Many2one('hr.department', string="Department", compute='_compute_department_and_job', store=True, readonly=True)
    job_id = fields.Many2one('hr.job', string="Job Position", compute='_compute_department_and_job', store=True, readonly=True)
    is_usd=fields.Boolean(string="is usd", compute="compute_monthly_salary", default=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('validated', 'Validated'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', track_visibility='onchange')

    @api.depends('employee_id','exchange_rate')
    def compute_monthly_salary(self):
        for rec in self:
           if  rec.employee_id.contract_id.currency_id.name != "ETB":
               rec.is_usd=True
               rec.monthly_salary=rec.employee_id.contract_id.wage*rec.exchange_rate
           else:
               rec.is_usd=False
               rec.monthly_salary = rec.employee_id.contract_id.wage


    @api.depends('employee_id')
    def _compute_department_and_job(self):
        for record in self:
            if record.employee_id:
                record.department_id = record.employee_id.department_id
                record.job_id = record.employee_id.contract_id.job_id
            else:
                record.department_id = False
                record.job_id = False

    @api.depends('monthly_salary', 'years_worked')
    def _compute_annual_salary(self):
        for record in self:
            record.annual_salary = record.monthly_salary * record.years_worked

    @api.depends('employee_id')
    def _compute_years_worked(self):
        for record in self:
            if record.employee_id:
                start_date = record.employee_id.contract_id.date_start
                end_date = record.employee_id.contract_id.date_end or fields.Date.today()
                delta = relativedelta(end_date, start_date)
                record.years_worked = delta.years
                record.months_worked = delta.months
                record.days_worked = delta.days

    @api.depends('years_worked', 'months_worked', 'days_worked', 'monthly_salary')
    def _compute_payout_amount(self):
        for record in self:
            payout_amount_years = 0.0
            payout_amount_months = 0.0
            payout_amount_days = 0.0

            if record.years_worked > 0:
                first_year_payout = record.monthly_salary
                subsequent_years_payout = (record.years_worked - 1) * (record.monthly_salary / 3)
                payout_amount_years = first_year_payout + subsequent_years_payout

            remaining_months = record.months_worked + (record.days_worked / 30)

            if remaining_months > 0:
                payout_amount_months = (record.monthly_salary / 12) * (remaining_months / 3)

            record.payout_amount = payout_amount_years + payout_amount_months

    @api.depends('payout_amount', 'monthly_salary')
    def _compute_payout_ratio(self):
        for record in self:
            if record.monthly_salary != 0.0:
                record.payout_ratio = record.payout_amount / record.monthly_salary
            else:
                record.payout_ratio = 0.0

    @api.depends('payout_ratio')
    def _compute_adjusted_payout(self):
        for record in self:
            a = record.monthly_salary
            if a <= 600:
                result = 0
            elif 601 <= a <= 1650:
                result = (a * 0.1 - 60)
            elif 1651 <= a <= 3200:
                result = (a * 0.15 - 142.50)
            elif 3201 <= a <= 5250:
                result = (a * 0.2 - 302.50)
            elif 5251 <= a <= 7800:
                result = (a * 0.25 - 565)
            elif 7801 <= a <= 10900:
                result = (a * 0.3 - 955)
            else:
                result = (a * 0.35 - 1500)

            integer_part = int(record.payout_ratio)
            record.adjusted_payout = result * integer_part

    @api.depends('payout_ratio')
    def _compute_adjusted_payout_after_dot(self):
        for record in self:
            fractional_part = record.payout_ratio - int(record.payout_ratio)
            a = record.monthly_salary * fractional_part
            if a <= 600:
                result = 0
            elif 601 <= a <= 1650:
                result = (a * 0.1 - 60)
            elif 1651 <= a <= 3200:
                result = (a * 0.15 - 142.50)
            elif 3201 <= a <= 5250:
                result = (a * 0.2 - 302.50)
            elif 5251 <= a <= 7800:
                result = (a * 0.25 - 565)
            elif 7801 <= a <= 10900:
                result = (a * 0.3 - 955)
            else:
                result = (a * 0.35 - 1500)

            record.adjusted_payout_after_dot = result

    @api.depends('adjusted_payout', 'adjusted_payout_after_dot')
    def _compute_total_adjusted_payout(self):
        for record in self:
            record.total_adjusted_payout = record.adjusted_payout + record.adjusted_payout_after_dot

    @api.depends('payout_amount', 'total_adjusted_payout')
    def _compute_total_payment(self):
        for record in self:
            record.total_payment = record.payout_amount - record.total_adjusted_payout

    def compute_severance(self):
        self._compute_payout_amount()
        self._compute_payout_ratio()
        self._compute_adjusted_payout()
        self._compute_adjusted_payout_after_dot()
        self._compute_total_adjusted_payout()
        self._compute_total_payment()

    def action_submit(self):
        self.state = 'submitted'
        self.compute_severance()

    def action_validate(self):
        self.state = 'validated'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_reset_draft(self):
        self.state = 'draft'
