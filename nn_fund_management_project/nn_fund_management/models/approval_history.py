# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class FundApprovalHistory(models.Model):
    _name = 'fund.approval.history'
    _description = 'Fund Approval / Action History'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    # Polymorphic-ish link: each workflow model sets exactly one of these
    allocation_id = fields.Many2one('fund.allocation', string='Allocation', ondelete='cascade')
    requisition_id = fields.Many2one('fund.requisition', string='Requisition', ondelete='cascade')
    transfer_id = fields.Many2one('fund.transfer', string='Transfer', ondelete='cascade')

    actor_id = fields.Many2one('res.users', string='Action By', required=True,
                                default=lambda self: self.env.user)
    approval_level = fields.Selection([
        ('submit', 'Submission'),
        ('gm', 'GM Approval'),
        ('md', 'MD Approval'),
        ('reject', 'Rejection'),
        ('cancel', 'Cancellation'),
        ('close', 'Closure'),
    ], string='Action Level', required=True)

    previous_state = fields.Char(string='Previous Status')
    new_state = fields.Char(string='New Status')
    comment = fields.Text(string='Comment')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    action_date = fields.Datetime(string='Action Date/Time', default=fields.Datetime.now, required=True)

    @api.depends('approval_level', 'actor_id', 'action_date')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "%s by %s on %s" % (
                dict(rec._fields['approval_level'].selection).get(rec.approval_level, ''),
                rec.actor_id.name or '',
                rec.action_date or '',
            )

    def unlink(self):
        # Audit records are immutable once created — never deletable through the UI/ORM.
        raise UserError("Approval history records cannot be deleted. "
                         "They form a permanent audit trail.")

    def write(self, vals):
        # Audit records are append-only — never editable after creation.
        raise UserError("Approval history records cannot be modified once created.")
