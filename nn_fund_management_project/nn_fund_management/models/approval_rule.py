# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FundApprovalRule(models.Model):
    """Amount-based approval routing rules.

    When a request is submitted, the mixin checks these rules (ordered by
    min_amount desc) and routes to the first matching rule.  If no rule
    matches, the default two-level GM→MD flow applies.

    Rules are scoped per transaction type and per company.
    """
    _name = 'fund.approval.rule'
    _description = 'Fund Approval Rule'
    _order = 'min_amount desc'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True)

    transaction_type = fields.Selection([
        ('allocation', 'Allocation'),
        ('requisition', 'Requisition'),
        ('transfer', 'Transfer'),
        ('all', 'All Types'),
    ], string='Transaction Type', required=True, default='all')

    min_amount = fields.Monetary(
        string='Minimum Amount', required=True,
        help='Rule applies when the request amount is >= this value.')
    max_amount = fields.Monetary(
        string='Maximum Amount',
        help='Rule applies when the request amount is <= this value. '
             'Leave empty for no upper bound.')
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', store=True)

    # ── Approval level configuration ─────────────────────────────────────
    require_gm = fields.Boolean(
        string='Require GM Approval', default=True)
    require_md = fields.Boolean(
        string='Require MD Approval', default=True)

    # Optional: route to specific users instead of any group member
    gm_approver_id = fields.Many2one(
        'res.users', string='Specific GM Approver',
        domain="[('groups_id.name', 'like', 'GM Approver')]",
        help='If set, only this user can perform the GM approval for matching requests.')
    md_approver_id = fields.Many2one(
        'res.users', string='Specific MD Approver',
        domain="[('groups_id.name', 'like', 'MD Approver')]",
        help='If set, only this user can perform the MD approval for matching requests.')

    description = fields.Text(string='Description / Notes')

    _sql_constraints = [
        ('min_amount_positive', 'CHECK(min_amount >= 0)',
         'Minimum amount must be zero or positive.'),
    ]

    @api.constrains('min_amount', 'max_amount')
    def _check_amount_range(self):
        for rule in self:
            if rule.max_amount and rule.max_amount < rule.min_amount:
                raise ValidationError(
                    "Maximum amount (%.2f) must be greater than or equal to "
                    "minimum amount (%.2f)." % (rule.max_amount, rule.min_amount))

    @api.constrains('require_gm', 'require_md')
    def _check_at_least_one_level(self):
        for rule in self:
            if not rule.require_gm and not rule.require_md:
                raise ValidationError(
                    "An approval rule must require at least one approval level "
                    "(GM or MD).")

    def _matches(self, transaction_type, amount):
        """Return True if this rule applies to the given type and amount."""
        self.ensure_one()
        if not self.active:
            return False
        if self.transaction_type not in (transaction_type, 'all'):
            return False
        if amount < self.min_amount:
            return False
        if self.max_amount and amount > self.max_amount:
            return False
        return True

    @api.model
    def get_rule_for(self, transaction_type, amount, company_id=None):
        """Return the best-matching active rule for a request, or None.

        Rules are searched in descending min_amount order so the most
        specific (highest threshold) rule wins when ranges overlap.
        """
        company_id = company_id or self.env.company.id
        rules = self.search([
            ('active', '=', True),
            ('company_id', '=', company_id),
        ])
        for rule in rules:
            if rule._matches(transaction_type, amount):
                return rule
        return None
