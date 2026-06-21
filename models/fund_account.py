# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FundAccount(models.Model):
    _name = 'fund.account'
    _description = 'Fund Account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Account Name', required=True, tracking=True)
    account_type = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ], string='Account Type', default='bank', required=True, tracking=True)

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', store=True, readonly=True)

    active = fields.Boolean(default=True)

    # ── Balance fields (all computed, all stored, never manually editable) ──
    total_received = fields.Monetary(
        string='Total Received', compute='_compute_balances', store=True,
        currency_field='currency_id',
        help='Sum of all confirmed incoming funds for this account.')
    unassigned_balance = fields.Monetary(
        string='Unassigned Balance', compute='_compute_balances', store=True,
        currency_field='currency_id',
        help='Available funds not yet allocated, held, or assigned.')
    held_amount = fields.Monetary(
        string='Held Amount', compute='_compute_balances', store=True,
        currency_field='currency_id',
        help='Amount on hold for pending allocation requests.')
    assigned_amount = fields.Monetary(
        string='Total Assigned', compute='_compute_balances', store=True,
        currency_field='currency_id',
        help='Amount that has been approved and assigned to projects or expense heads.')

    incoming_fund_ids = fields.One2many(
        'fund.incoming', 'fund_account_id', string='Incoming Funds')
    allocation_ids = fields.One2many(
        'fund.allocation', 'fund_account_id', string='Allocations')

    _sql_constraints = [
        ('balance_non_negative_check',
         'CHECK(unassigned_balance >= 0)',
         'Unassigned balance cannot be negative.'),
    ]

    @api.depends(
        'incoming_fund_ids.amount', 'incoming_fund_ids.state',
        'allocation_ids.amount', 'allocation_ids.state',
    )
    def _compute_balances(self):
        for account in self:
            confirmed_incoming = account.incoming_fund_ids.filtered(
                lambda r: r.state == 'confirmed')
            total_received = sum(confirmed_incoming.mapped('amount'))

            held = sum(account.allocation_ids.filtered(
                lambda r: r.state in ('submitted', 'gm_approved')
            ).mapped('amount'))

            assigned = sum(account.allocation_ids.filtered(
                lambda r: r.state == 'approved'
            ).mapped('amount'))

            account.total_received = total_received
            account.held_amount = held
            account.assigned_amount = assigned
            account.unassigned_balance = total_received - held - assigned

    @api.constrains('unassigned_balance')
    def _check_balance_non_negative(self):
        for account in self:
            if account.unassigned_balance < 0:
                raise ValidationError(
                    "Account '%s' cannot have a negative unassigned balance."
                    % account.name)
