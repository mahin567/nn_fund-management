# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ExpenseHead(models.Model):
    _name = 'fund.expense.head'
    _description = 'Expense Head'
    _order = 'name'

    name = fields.Char(string='Expense Head', required=True)
    code = fields.Char(string='Code')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', store=True)
    active = fields.Boolean(default=True)

    # ── Balance fields ──
    total_allocated = fields.Monetary(
        string='Total Allocated', compute='_compute_balances', store=True,
        currency_field='currency_id')
    available_fund = fields.Monetary(
        string='Available Fund', compute='_compute_balances', store=True,
        currency_field='currency_id')
    requisition_hold = fields.Monetary(
        string='Requisition Hold', compute='_compute_balances', store=True,
        currency_field='currency_id')
    transfer_hold = fields.Monetary(
        string='Transfer Hold', compute='_compute_balances', store=True,
        currency_field='currency_id')
    approved_unspent = fields.Monetary(
        string='Approved but Unspent', compute='_compute_balances', store=True,
        currency_field='currency_id')
    total_spent = fields.Monetary(
        string='Total Spent', compute='_compute_balances', store=True,
        currency_field='currency_id')
    incoming_transfers = fields.Monetary(
        string='Incoming Transfers', compute='_compute_balances', store=True,
        currency_field='currency_id')
    outgoing_transfers = fields.Monetary(
        string='Outgoing Transfers', compute='_compute_balances', store=True,
        currency_field='currency_id')

    allocation_ids = fields.One2many(
        'fund.allocation', 'expense_head_id', string='Allocations')
    requisition_ids = fields.One2many(
        'fund.requisition', 'expense_head_id', string='Requisitions')
    transfer_in_ids = fields.One2many(
        'fund.transfer', 'destination_expense_head_id', string='Transfers In')
    transfer_out_ids = fields.One2many(
        'fund.transfer', 'source_expense_head_id', string='Transfers Out')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, company_id)',
         'Expense head code must be unique per company.'),
    ]

    @api.depends(
        'allocation_ids.amount', 'allocation_ids.state',
        'requisition_ids.amount', 'requisition_ids.state',
        'requisition_ids.billed_amount',
        'transfer_in_ids.amount', 'transfer_in_ids.state',
        'transfer_out_ids.amount', 'transfer_out_ids.state',
    )
    def _compute_balances(self):
        for head in self:
            allocated = sum(head.allocation_ids.filtered(
                lambda r: r.state == 'approved').mapped('amount'))

            req_hold = sum(head.requisition_ids.filtered(
                lambda r: r.state in ('submitted', 'gm_approved')
            ).mapped('amount'))

            req_reserved = sum(head.requisition_ids.filtered(
                lambda r: r.state == 'approved'
            ).mapped(lambda r: r.amount - r.billed_amount))

            spent = sum(head.requisition_ids.mapped('billed_amount'))

            transfer_hold = sum(head.transfer_out_ids.filtered(
                lambda r: r.state in ('submitted', 'gm_approved')
            ).mapped('amount'))

            incoming = sum(head.transfer_in_ids.filtered(
                lambda r: r.state == 'approved').mapped('amount'))
            outgoing = sum(head.transfer_out_ids.filtered(
                lambda r: r.state == 'approved').mapped('amount'))

            head.total_allocated = allocated
            head.requisition_hold = req_hold
            head.transfer_hold = transfer_hold
            head.total_spent = spent
            head.approved_unspent = req_reserved
            head.incoming_transfers = incoming
            head.outgoing_transfers = outgoing
            head.available_fund = (
                allocated + incoming - outgoing - req_hold
                - req_reserved - transfer_hold
            )
