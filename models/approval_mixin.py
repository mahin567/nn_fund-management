# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError


class FundApprovalMixin(models.AbstractModel):
    """Shared two-level (GM -> MD) approval workflow.

    Concrete models (fund.allocation, fund.requisition, fund.transfer)
    inherit this mixin and must implement:
      - _get_history_model_field(): name of the M2O field on
        fund.approval.history that links back to this record
        (e.g. 'allocation_id')
      - _on_submit() / _on_approve() / _on_reject() / _on_cancel():
        hooks for model-specific balance logic
    """
    _name = 'fund.approval.mixin'
    _description = 'Fund Approval Workflow Mixin'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('gm_approved', 'GM Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    gm_approver_id = fields.Many2one('res.users', string='GM Approver', tracking=True)
    gm_approval_date = fields.Datetime(string='GM Approval Date')
    gm_comment = fields.Text(string='GM Comment')

    md_approver_id = fields.Many2one('res.users', string='MD Approver', tracking=True)
    md_approval_date = fields.Datetime(string='MD Approval Date')
    md_comment = fields.Text(string='MD Comment')

    requested_by = fields.Many2one(
        'res.users', string='Requested By', default=lambda self: self.env.user,
        required=True, readonly=True)

    # ── Hooks to be implemented by concrete models ──────────────────────────
    def _get_history_link_field(self):
        raise NotImplementedError

    def _on_submit(self):
        """Apply hold logic. Override in concrete model."""
        pass

    def _on_gm_approve(self):
        pass

    def _on_md_approve(self):
        """Apply final approval logic (release hold -> assign). Override."""
        pass

    def _on_reject(self):
        """Return held amount. Override in concrete model."""
        pass

    def _on_cancel(self):
        """Return held amount. Override in concrete model."""
        pass

    # ── Server-side permission checks (never rely on hidden buttons) ───────
    def _check_can_submit(self):
        if not self.env.user.has_group('nn_fund_management.group_fund_user'):
            raise AccessError("You do not have permission to submit fund requests.")

    def _check_can_approve_gm(self):
        if not self.env.user.has_group('nn_fund_management.group_gm_approver'):
            raise AccessError("Only an authorized GM Approver can perform this action.")
        if self.requested_by == self.env.user and not self.env.user.has_group(
                'nn_fund_management.group_fund_admin'):
            raise AccessError("You cannot approve your own request.")

    def _check_can_approve_md(self):
        if not self.env.user.has_group('nn_fund_management.group_md_approver'):
            raise AccessError("Only an authorized MD Approver can perform this action.")
        if self.requested_by == self.env.user and not self.env.user.has_group(
                'nn_fund_management.group_fund_admin'):
            raise AccessError("You cannot approve your own request.")

    # ── Workflow actions ─────────────────────────────────────────────────
    def action_submit(self):
        for rec in self:
            rec._check_can_submit()
            if rec.state != 'draft':
                raise UserError("Only draft records can be submitted.")
            prev = rec.state
            rec._on_submit()
            rec.state = 'submitted'
            rec._log_history('submit', prev, 'submitted', self.env.user)

    def action_gm_approve(self, comment=None):
        for rec in self:
            rec._check_can_approve_gm()
            if rec.state != 'submitted':
                raise UserError("This record is not awaiting GM approval.")
            prev = rec.state
            rec._on_gm_approve()
            rec.write({
                'state': 'gm_approved',
                'gm_approver_id': self.env.user.id,
                'gm_approval_date': fields.Datetime.now(),
                'gm_comment': comment,
            })
            rec._log_history('gm', prev, 'gm_approved', self.env.user, comment)

    def action_md_approve(self, comment=None):
        for rec in self:
            rec._check_can_approve_md()
            if rec.state != 'gm_approved':
                raise UserError("GM approval must be completed before MD approval.")
            prev = rec.state
            rec._on_md_approve()
            rec.write({
                'state': 'approved',
                'md_approver_id': self.env.user.id,
                'md_approval_date': fields.Datetime.now(),
                'md_comment': comment,
            })
            rec._log_history('md', prev, 'approved', self.env.user, comment)

    def action_reject(self, comment=None):
        for rec in self:
            if rec.state not in ('submitted', 'gm_approved'):
                raise UserError("Only submitted or GM-approved records can be rejected.")
            is_gm_stage = rec.state == 'submitted'
            if is_gm_stage:
                rec._check_can_approve_gm()
            else:
                rec._check_can_approve_md()
            prev = rec.state
            rec._on_reject()
            rec.write({'state': 'rejected'})
            rec._log_history('reject', prev, 'rejected', self.env.user, comment)

    def action_cancel(self):
        for rec in self:
            if rec.state in ('rejected', 'cancelled'):
                raise UserError("This record is already closed.")
            if not (self.env.user.has_group('nn_fund_management.group_fund_admin')
                    or rec.requested_by == self.env.user and rec.state == 'draft'):
                raise AccessError("You do not have permission to cancel this record.")
            prev = rec.state
            rec._on_cancel()
            rec.write({'state': 'cancelled'})
            rec._log_history('cancel', prev, 'cancelled', self.env.user)

    def _log_history(self, level, prev_state, new_state, actor, comment=None):
        self.ensure_one()
        link_field = self._get_history_link_field()
        self.env['fund.approval.history'].create({
            link_field: self.id,
            'actor_id': actor.id,
            'approval_level': level,
            'previous_state': prev_state,
            'new_state': new_state,
            'comment': comment,
            'amount': getattr(self, 'amount', 0.0),
        })
