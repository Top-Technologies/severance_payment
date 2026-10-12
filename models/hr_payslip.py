from odoo import api, models, Command


class PayslipSeverance(models.Model):
    _inherit = 'hr.payslip'

    def _severance_payments(self):
        self.ensure_one()
        if not self.employee_id or not self.date_from or not self.date_to:
            return self.env['severance.payment']
        return self.env['severance.payment'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validated'),
            ('payment_date', '>=', self.date_from),
            ('payment_date', '<=', self.date_to),
        ])

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to')
    def _compute_input_line_ids(self):
        super()._compute_input_line_ids()
        tax_type = self.env.ref('severance_payment.input_taxsev', raise_if_not_found=False)
        pay_type = self.env.ref('severance_payment.input_paysev', raise_if_not_found=False)
        if not tax_type or not pay_type:
            return
        for slip in self:
            lines_to_remove = slip.input_line_ids.filtered(
                lambda line: line.input_type_id in (tax_type, pay_type)
            )
            commands = [Command.unlink(line.id) for line in lines_to_remove]
            payments = slip._severance_payments()
            if payments:
                commands.append(Command.create({
                    'name': tax_type.name,
                    'amount': sum(payments.mapped('total_adjusted_payout')),
                    'input_type_id': tax_type.id,
                }))
                commands.append(Command.create({
                    'name': pay_type.name,
                    'amount': sum(payments.mapped('total_payment')),
                    'input_type_id': pay_type.id,
                }))
            if commands:
                slip.update({'input_line_ids': commands})

    def action_payslip_done(self):
        for slip in self:
            slip._severance_payments().write({'state': 'paid'})
        return super().action_payslip_done()
