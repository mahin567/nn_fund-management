# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class FundAllocation(models.Model):
    _name = 'fund.allocation'
    _description = 'Fund Allocation Request'
    _inherit = ['fund.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    name = fields.Char(
        string='Request Number', required=True, copy=False, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('fund.allocation') or 'New')

    fund_account_id = fields.Many2one(
        'fund.account', string='Fund Account', required=True, tracking=True,
       domain="[]")

    # Exactly one of these two must be set (enforced by constraint below)
    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    expense_head_id = fields.Many2one('fund.expense.head', string='Expense Head', tracking=True)

    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', related='fund_account_id.currency_id', store=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company, required=True)

    purpose = fields.Text(string='Purpose')
    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, required=True)
    attachment = fields.Binary(string='Attachment')
    attachment_filename = fields.Char(string='Attachment Filename')

    history_ids = fields.One2many(
        'fund.approval.history', 'allocation_id', string='Approval History')

    _sql_constraints = [
        ('amount_positive_check', 'CHECK(amount > 0)',
         'Allocation amount must be positive.'),
    ]

    @api.constrains('project_id', 'expense_head_id')
    def _check_single_target(self):
        for rec in self:
            if bool(rec.project_id) == bool(rec.expense_head_id):
                raise ValidationError(
                    "An allocation must target either a Project or an Expense Head, not both.")

    @api.constrains('amount', 'fund_account_id', 'state')
    def _check_sufficient_balance(self):
        for rec in self:
            if rec.state == 'draft':
                continue
            # On submit, balance is already deducted via compute; re-validate
            # against what *would* remain available before this record's own hold.
            account = rec.fund_account_id
            other_holds = sum(account.allocation_ids.filtered(
                lambda r: r.id != rec.id and r.state in ('submitted', 'gm_approved', 'approved')
            ).mapped('amount'))
            if rec.amount + other_holds > account.total_received:
                raise ValidationError(
                    "Allocation amount (%.2f) exceeds the available unassigned "
                    "balance of account '%s'." % (rec.amount, account.name))

    def _get_history_link_field(self):
        return 'allocation_id'

    def _on_submit(self):
        self.ensure_one()
        if self.amount > self.fund_account_id.unassigned_balance:
            raise UserError(
                "Cannot submit: requested amount (%.2f) exceeds the available "
                "unassigned balance (%.2f) of account '%s'." % (
                    self.amount, self.fund_account_id.unassigned_balance,
                    self.fund_account_id.name))
        # Balances are computed fields driven by state changes — no manual writes needed.
        # Changing state to 'submitted' automatically moves this amount into held_amount
        # via fund.account._compute_balances().

    def _on_md_approve(self):
        self.ensure_one()
        # Moving state to 'approved' automatically shifts the amount from
        # held_amount to assigned_amount via the compute method. Nothing else to do.

    def _on_reject(self):
        self.ensure_one()
        # State change back to 'rejected' automatically excludes this amount
        # from held_amount, returning it to unassigned_balance via compute.

    def _on_cancel(self):
        self.ensure_one()
        # Same as reject — compute fields handle the balance restoration.
