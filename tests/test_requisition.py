# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestFundRequisition(TransactionCase):

    def setUp(self):
        super().setUp()
        self.account = self.env['fund.account'].create({'name': 'Test Account'})
        incoming = self.env['fund.incoming'].create({
            'fund_account_id': self.account.id,
            'amount': 1000000.0,
            'transaction_reference': 'TXN-REQ-1',
        })
        incoming.action_confirm()

        self.expense_head = self.env['fund.expense.head'].create({
            'name': 'Test Expense Head', 'code': 'TEH2',
        })

        gm_group = self.env.ref('nn_fund_management.group_gm_approver')
        md_group = self.env.ref('nn_fund_management.group_md_approver')
        self.env.user.write({'groups_id': [(4, gm_group.id), (4, md_group.id)]})

        allocation = self.env['fund.allocation'].create({
            'fund_account_id': self.account.id,
            'expense_head_id': self.expense_head.id,
            'amount': 800000.0,
        })
        allocation.action_submit()
        allocation.action_gm_approve()
        allocation.action_md_approve()

    def test_requisition_hold_and_approval(self):
        req = self.env['fund.requisition'].create({
            'expense_head_id': self.expense_head.id,
            'amount': 150000.0,
        })
        req.action_submit()
        self.assertEqual(req.state, 'submitted')
        req.action_gm_approve()
        req.action_md_approve()
        self.assertEqual(req.state, 'approved')
        self.assertEqual(req.remaining_billable, 150000.0)

    def test_requisition_exceeding_balance_blocked(self):
        req = self.env['fund.requisition'].create({
            'expense_head_id': self.expense_head.id,
            'amount': 9000000.0,
        })
        with self.assertRaises(UserError):
            req.action_submit()
