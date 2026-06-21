# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError


class FundIncoming(models.Model):
    _name = 'fund.incoming'
    _description = 'Incoming Fund'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('fund.incoming') or 'New')

    fund_account_id = fields.Many2one(
        'fund.account', string='Fund Account', required=True, tracking=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', related='fund_account_id.currency_id', store=True)
    company_id = fields.Many2one(
        'res.company', related='fund_account_id.company_id', store=True)

    transaction_reference = fields.Char(string='Transaction Reference', required=True)
    source = fields.Char(string='Sender / Source')
    description = fields.Text(string='Description')
    attachment = fields.Binary(string='Attachment')
    attachment_filename = fields.Char(string='Attachment Filename')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('pending_verification', 'Pending Verification'),  # used by bank-email bonus feature
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    # Bonus: bank email integration traceability
    source_email_message_id = fields.Char(string='Source Email Message-ID', copy=False)

    _sql_constraints = [
        ('amount_positive_check', 'CHECK(amount > 0)', 'Incoming fund amount must be positive.'),
        ('txn_ref_unique_per_account',
         'UNIQUE(fund_account_id, transaction_reference)',
         'This transaction reference has already been used for this fund account.'),
    ]

    def action_confirm(self):
        for rec in self:
            if rec.state not in ('draft', 'pending_verification'):
                raise UserError("Only draft or pending-verification records can be confirmed.")
            if not self.env.user.has_group('nn_fund_management.group_finance_user'):
                raise AccessError(
                    "Only an authorized Finance User can confirm incoming funds.")
            rec.state = 'confirmed'
            # fund_account_id.total_received / unassigned_balance recompute
            # automatically via the compute dependency on incoming_fund_ids.

    def unlink(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(
                    "Confirmed incoming funds cannot be deleted. "
                    "Use a proper reversal process instead.")
        return super().unlink()
