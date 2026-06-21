# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class FundRequisition(models.Model):
    _name = 'fund.requisition'
    _description = 'Fund Requisition'
    _inherit = ['fund.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    name = fields.Char(
        string='Requisition Number', required=True, copy=False, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('fund.requisition') or 'New')

    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    expense_head_id = fields.Many2one('fund.expense.head', string='Expense Head', tracking=True)

    amount = fields.Monetary(string='Requested Amount', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company, required=True)

    purpose = fields.Text(string='Purpose')
    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, required=True)
    required_date = fields.Date(string='Required Date')
    attachment = fields.Binary(string='Attachment')
    attachment_filename = fields.Char(string='Attachment Filename')

    billed_amount = fields.Monetary(
        string='Billed Amount', compute='_compute_billed_amount', store=True,
        currency_field='currency_id')
    remaining_billable = fields.Monetary(
        string='Remaining Billable', compute='_compute_billed_amount', store=True,
        currency_field='currency_id')

    bill_ids = fields.One2many('fund.bill', 'requisition_id', string='Bills')
    history_ids = fields.One2many(
        'fund.approval.history', 'requisition_id', string='Approval History')

    # Extended states beyond the base mixin (Closed is requisition-specific)
    state = fields.Selection(selection_add=[('closed', 'Closed')], ondelete={'closed': 'cascade'})

    _sql_constraints = [
        ('amount_positive_check', 'CHECK(amount > 0)',
         'Requisition amount must be positive.'),
    ]

    @api.constrains('project_id', 'expense_head_id')
    def _check_single_target(self):
        for rec in self:
            if bool(rec.project_id) == bool(rec.expense_head_id):
                raise ValidationError(
                    "A requisition must target either a Project or an Expense Head, not both.")

    @api.depends('bill_ids.amount', 'bill_ids.state', 'amount')
    def _compute_billed_amount(self):
        for rec in self:
            billed = sum(rec.bill_ids.filtered(
                lambda b: b.state == 'posted').mapped('amount'))
            rec.billed_amount = billed
            rec.remaining_billable = rec.amount - billed if rec.state == 'approved' else 0.0

    def _get_target_balance_record(self):
        self.ensure_one()
        return self.project_id or self.expense_head_id

    def _get_history_link_field(self):
        return 'requisition_id'

    def _on_submit(self):
        self.ensure_one()
        target = self.expense_head_id
        if target and self.amount > target.available_fund:
            raise UserError(
                "Cannot submit: requested amount (%.2f) exceeds available "
                "balance (%.2f)." % (self.amount, target.available_fund))
        # held via compute on expense_head/project balance

    def _on_md_approve(self):
        self.ensure_one()
        # Amount remains reserved (held -> approved_unspent) via compute fields.

    def _on_reject(self):
        self.ensure_one()
        # Released back to available_fund via compute fields.

    def _on_cancel(self):
        self.ensure_one()

    def action_close(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError("Only approved requisitions can be closed.")
            if rec.remaining_billable > 0:
                raise UserError(
                    "Cannot close: %.2f is still unbilled. Either bill it or "
                    "explicitly release it first." % rec.remaining_billable)
            prev = rec.state
            rec.write({'state': 'closed'})
            rec._log_history('close', prev, 'closed', self.env.user)
