# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError


class FundApprovalMixin(models.AbstractModel):
    """Shared two-level (GM -> MD) approval workflow.

    Concrete models (fund.allocation, fund.requisition, fund.transfer)
    inherit this mixin and must implement:
      - _get_history_link_field(): name of the M2O field on
        fund.approval.history that links back to this record
        (e.g. 'allocation_id')
      - _on_submit() / _on_md_approve() / _on_reject() / _on_cancel():
        hooks for model-specific balance logic

    When a matching fund.approval.rule exists for the request amount and
    type, the rule overrides the default two-level flow:
      - If require_gm=False: submit goes directly to gm_approved state
        (bypassing GM), and MD approves next.
      - If require_md=False: GM approval is the final step and
        transitions directly to 'approved'.
      - Specific approver users on the rule restrict who may approve
        at each level.
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

    # Resolved at submit time and stored so it survives rule edits
    applied_rule_id = fields.Many2one(
        'fund.approval.rule', string='Applied Approval Rule',
        readonly=True, copy=False,
        help='The approval rule matched at submission time. Changing rules '
             'after submission does not affect in-flight requests.')

    # ── Hooks ──────────────────────────────────────────────────────────────
    def _get_history_link_field(self):
        raise NotImplementedError

    def _get_transaction_type(self):
        """Return 'allocation', 'requisition', or 'transfer'."""
        name_map = {
            'fund.allocation': 'allocation',
            'fund.requisition': 'requisition',
            'fund.transfer': 'transfer',
        }
        return name_map.get(self._name, 'allocation')

    def _on_submit(self):
        pass

    def _on_gm_approve(self):
        pass

    def _on_md_approve(self):
        pass

    def _on_reject(self):
        pass

    def _on_cancel(self):
        pass

    # ── Rule helpers ───────────────────────────────────────────────────────
    def _resolve_rule(self):
        """Return the best matching fund.approval.rule or None."""
        self.ensure_one()
        amount = getattr(self, 'amount', 0.0) or 0.0
        tx_type = self._get_transaction_type()
        company_id = getattr(self, 'company_id', self.env.company).id
        return self.env['fund.approval.rule'].get_rule_for(tx_type, amount, company_id)

    def _rule_requires_gm(self):
        self.ensure_one()
        rule = self.applied_rule_id
        return rule.require_gm if rule else True

    def _rule_requires_md(self):
        self.ensure_one()
        rule = self.applied_rule_id
        return rule.require_md if rule else True

    # ── Permission checks ──────────────────────────────────────────────────
    def _check_can_submit(self):
        if not self.env.user.has_group('nn_fund_management.group_fund_user'):
            raise AccessError("You do not have permission to submit fund requests.")

    def _check_can_approve_gm(self):
        rule = self.applied_rule_id
        # If rule specifies a particular approver, enforce it
        if rule and rule.gm_approver_id and self.env.user != rule.gm_approver_id:
            raise AccessError(
                "This request must be GM-approved by %s (as per approval rule '%s')."
                % (rule.gm_approver_id.name, rule.name))
        if not self.env.user.has_group('nn_fund_management.group_gm_approver'):
            raise AccessError("Only an authorized GM Approver can perform this action.")
        if (self.requested_by == self.env.user
                and not self.env.user.has_group('nn_fund_management.group_fund_admin')):
            raise AccessError("You cannot approve your own request.")

    def _check_can_approve_md(self):
        rule = self.applied_rule_id
        if rule and rule.md_approver_id and self.env.user != rule.md_approver_id:
            raise AccessError(
                "This request must be MD-approved by %s (as per approval rule '%s')."
                % (rule.md_approver_id.name, rule.name))
        if not self.env.user.has_group('nn_fund_management.group_md_approver'):
            raise AccessError("Only an authorized MD Approver can perform this action.")
        if (self.requested_by == self.env.user
                and not self.env.user.has_group('nn_fund_management.group_fund_admin')):
            raise AccessError("You cannot approve your own request.")

    # ── Workflow actions ───────────────────────────────────────────────────
    def action_submit(self):
        for rec in self:
            rec._check_can_submit()
            if rec.state != 'draft':
                raise UserError("Only draft records can be submitted.")
            prev = rec.state
            rec._on_submit()

            # Resolve and store the matching rule at submission time
            rule = rec._resolve_rule()
            rec.applied_rule_id = rule.id if rule else False

            if rule and not rule.require_gm:
                # Skip GM — go directly to gm_approved so MD can act next
                rec.state = 'gm_approved'
                rec._log_history('submit', prev, 'gm_approved', self.env.user,
                                 comment='GM step skipped by rule: %s' % rule.name)
            else:
                rec.state = 'submitted'
                rec._log_history('submit', prev, 'submitted', self.env.user)

    def action_gm_approve(self, comment=None):
        for rec in self:
            rec._check_can_approve_gm()
            if rec.state != 'submitted':
                raise UserError("This record is not awaiting GM approval.")
            prev = rec.state
            rec._on_gm_approve()

            if not rec._rule_requires_md():
                # No MD step — GM approval is final
                rec._on_md_approve()
                rec.write({
                    'state': 'approved',
                    'gm_approver_id': self.env.user.id,
                    'gm_approval_date': fields.Datetime.now(),
                    'gm_comment': comment,
                })
                rec._log_history('gm', prev, 'approved', self.env.user,
                                 comment=(comment or '') + ' [MD step skipped by rule: %s]'
                                 % rec.applied_rule_id.name)
            else:
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
