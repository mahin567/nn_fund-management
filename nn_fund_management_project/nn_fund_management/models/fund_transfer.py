# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class FundTransfer(models.Model):
    _name = 'fund.transfer'
    _description = 'Fund Transfer'
    _inherit = ['fund.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    name = fields.Char(
        string='Transfer Number', required=True, copy=False, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('fund.transfer') or 'New')

    source_project_id = fields.Many2one('project.project', string='Source Project')
    source_expense_head_id = fields.Many2one('fund.expense.head', string='Source Expense Head')

    destination_project_id = fields.Many2one('project.project', string='Destination Project')
    destination_expense_head_id = fields.Many2one('fund.expense.head', string='Destination Expense Head')

    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True)

    reason = fields.Text(string='Reason')
    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, required=True)

    history_ids = fields.One2many(
        'fund.approval.history', 'transfer_id', string='Approval History')

    _sql_constraints = [
        ('amount_positive_check', 'CHECK(amount > 0)', 'Transfer amount must be positive.'),
    ]

    @api.constrains('source_project_id', 'source_expense_head_id')
    def _check_single_source(self):
        for rec in self:
            if bool(rec.source_project_id) == bool(rec.source_expense_head_id):
                raise ValidationError(
                    "A transfer must have exactly one source: a Project or an Expense Head.")

    @api.constrains('destination_project_id', 'destination_expense_head_id')
    def _check_single_destination(self):
        for rec in self:
            if bool(rec.destination_project_id) == bool(rec.destination_expense_head_id):
                raise ValidationError(
                    "A transfer must have exactly one destination: a Project or an Expense Head.")

    @api.constrains(
        'source_project_id', 'source_expense_head_id',
        'destination_project_id', 'destination_expense_head_id')
    def _check_source_destination_differ(self):
        for rec in self:
            source = rec.source_project_id or rec.source_expense_head_id
            destination = rec.destination_project_id or rec.destination_expense_head_id
            if source and destination and source == destination:
                raise ValidationError("Source and destination cannot be the same.")

    def _get_source_balance_record(self):
        self.ensure_one()
        return self.source_project_id or self.source_expense_head_id

    def _get_history_link_field(self):
        return 'transfer_id'

    def _on_submit(self):
        self.ensure_one()
        source = self._get_source_balance_record()
        if source and hasattr(source, 'available_fund') and self.amount > source.available_fund:
            raise UserError(
                "Cannot submit: transfer amount (%.2f) exceeds the source's "
                "available balance (%.2f)." % (self.amount, source.available_fund))

    def _on_md_approve(self):
        self.ensure_one()
        # Destination balance increases and source transfer_hold clears via
        # the compute dependencies on transfer_in_ids / transfer_out_ids.

    def _on_reject(self):
        self.ensure_one()
        # Source available_fund is restored automatically via compute.

    def _on_cancel(self):
        self.ensure_one()
