# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class ReleaseUnusedFundsWizard(models.TransientModel):
    """Pop-up wizard to release the unbilled portion of an approved
    requisition back to its project/expense head balance, and optionally
    close the requisition in the same step.

    Triggered from a button on the fund.requisition form view.
    """
    _name = 'fund.release.unused.wizard'
    _description = 'Release Unused Requisition Funds'

    requisition_id = fields.Many2one(
        'fund.requisition', string='Requisition', required=True, readonly=True)

    approved_amount = fields.Monetary(
        string='Approved Amount', related='requisition_id.amount', readonly=True)
    billed_amount = fields.Monetary(
        string='Billed Amount', related='requisition_id.billed_amount', readonly=True)
    unused_amount = fields.Monetary(
        string='Unused Amount', compute='_compute_unused_amount', readonly=True)
    currency_id = fields.Many2one(
        'res.currency', related='requisition_id.currency_id', readonly=True)

    close_after_release = fields.Boolean(
        string='Close requisition after releasing', default=True)
    comment = fields.Text(string='Reason for Release')

    @api.depends('requisition_id.amount', 'requisition_id.billed_amount')
    def _compute_unused_amount(self):
        for wizard in self:
            wizard.unused_amount = (
                wizard.requisition_id.amount - wizard.requisition_id.billed_amount)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            defaults['requisition_id'] = active_id
        return defaults

    def action_release(self):
        self.ensure_one()
        req = self.requisition_id

        if req.state != 'approved':
            raise UserError("Only approved requisitions can have funds released.")
        if self.unused_amount <= 0:
            raise UserError("There is no unused amount to release on this requisition.")

        # The release itself doesn't need a manual balance write: closing the
        # requisition (state -> 'closed') removes it from the 'approved'
        # filter used in approved_unspent / requisition_hold computations,
        # so the unused amount automatically flows back into available_fund
        # via the project/expense_head compute methods.
        self.env['fund.approval.history'].create({
            'requisition_id': req.id,
            'actor_id': self.env.user.id,
            'approval_level': 'close',
            'previous_state': req.state,
            'new_state': 'closed' if self.close_after_release else req.state,
            'comment': self.comment or (
                'Released unused amount of %.2f' % self.unused_amount),
            'amount': self.unused_amount,
        })

        if self.close_after_release:
            # Bypass action_close()'s "remaining_billable must be 0" guard —
            # that guard exists for the *billing* path; here we are
            # deliberately releasing the unused amount, which is a distinct,
            # explicit action and is allowed to close with leftover budget.
            req.write({'state': 'closed'})

        return {'type': 'ir.actions.act_window_close'}