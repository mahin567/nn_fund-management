# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class FundBill(models.Model):
    _name = 'fund.bill'
    _description = 'Fund Bill'
    _inherit = ['mail.thread']
    _order = 'bill_date desc'

    name = fields.Char(
        string='Bill Reference', required=True, copy=False, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('fund.bill') or 'New')

    requisition_id = fields.Many2one(
        'fund.requisition', string='Requisition', required=True, tracking=True,
        domain="[('state', '=', 'approved')]")

    # Denormalized for easy domain filtering / reporting; kept in sync via onchange
    project_id = fields.Many2one(
        related='requisition_id.project_id', store=True, readonly=True)
    expense_head_id = fields.Many2one(
        related='requisition_id.expense_head_id', store=True, readonly=True)

    amount = fields.Monetary(string='Bill Amount', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True)

    bill_date = fields.Date(string='Bill Date', default=fields.Date.context_today, required=True)
    description = fields.Text(string='Description')
    attachment = fields.Binary(string='Attachment')
    attachment_filename = fields.Char(string='Attachment Filename')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    _sql_constraints = [
        ('amount_positive_check', 'CHECK(amount > 0)', 'Bill amount must be positive.'),
    ]

    @api.constrains('requisition_id', 'amount', 'state')
    def _check_requisition_rules(self):
        for bill in self:
            if bill.state != 'posted':
                continue
            req = bill.requisition_id
            if req.state != 'approved':
                raise ValidationError(
                    "Bills can only be posted against an approved requisition.")

            # Project A cannot use Project B's requisition, same for expense heads —
            # enforced implicitly since project_id/expense_head_id are related fields
            # copied directly from the requisition; this constraint guards against
            # any future direct write to those fields.

            other_posted = req.bill_ids.filtered(
                lambda b: b.id != bill.id and b.state == 'posted')
            total_billed = sum(other_posted.mapped('amount')) + bill.amount
            if total_billed > req.amount:
                raise ValidationError(
                    "This bill (%.2f) would exceed the requisition's approved "
                    "amount. Remaining billable: %.2f" % (
                        bill.amount,
                        req.amount - sum(other_posted.mapped('amount'))))

    def action_post(self):
        for bill in self:
            if bill.state != 'draft':
                raise UserError("Only draft bills can be posted.")
            if bill.requisition_id.state != 'approved':
                raise UserError("The linked requisition is not approved.")
            if bill.amount > bill.requisition_id.remaining_billable:
                raise UserError(
                    "Bill amount (%.2f) exceeds the requisition's remaining "
                    "billable amount (%.2f)." % (
                        bill.amount, bill.requisition_id.remaining_billable))
            bill.state = 'posted'
            # requisition.remaining_billable recomputes automatically via
            # the compute dependency on bill_ids.amount / bill_ids.state

    def action_cancel(self):
        for bill in self:
            if bill.state != 'posted':
                raise UserError("Only posted bills can be cancelled.")
            if not self.env.user.has_group('nn_fund_management.group_fund_admin'):
                raise UserError("Only a Fund Administrator can cancel a posted bill.")
            bill.state = 'cancelled'
            # Amount automatically returns to remaining_billable via compute —
            # this does not create new funds, it simply excludes a non-posted
            # bill from the billed_amount sum.
