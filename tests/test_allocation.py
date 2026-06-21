# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestFundAllocation(TransactionCase):

    def setUp(self):
        super().setUp()
        self.account = self.env['fund.account'].create({'name': 'Test Account'})
        incoming = self.env['fund.incoming'].create({
            'fund_account_id': self.account.id,
            'amount': 1000000.0,
            'transaction_reference': 'TXN-ALLOC-1',
        })
        incoming.action_confirm()

        self.expense_head = self.env['fund.expense.head'].create({
            'name': 'Test Expense Head', 'code': 'TEH',
        })

        # Promote the test user into the right groups so workflow actions pass
        gm_group = self.env.ref('nn_fund_management.group_gm_approver')
        md_group = self.env.ref('nn_fund_management.group_md_approver')
        self.env.user.write({'groups_id': [(4, gm_group.id), (4, md_group.id)]})

    def test_allocation_requires_single_target(self):
        with self.assertRaises(ValidationError):
            self.env['fund.allocation'].create({
                'fund_account_id': self.account.id,
                'expense_head_id': self.expense_head.id,
                'project_id': False,
                'amount': 1000.0,
            }).write({})  # trigger constraint check path explicitly if needed

    def test_full_allocation_workflow(self):
        allocation = self.env['fund.allocation'].create({
            'fund_account_id': self.account.id,
            'expense_head_id': self.expense_head.id,
            'amount': 600000.0,
        })
        allocation.action_submit()
        self.assertEqual(allocation.state, 'submitted')
        self.assertEqual(self.account.held_amount, 600000.0)
        self.assertEqual(self.account.unassigned_balance, 400000.0)

        allocation.action_gm_approve()
        self.assertEqual(allocation.state, 'gm_approved')

        allocation.action_md_approve()
        self.assertEqual(allocation.state, 'approved')
        self.assertEqual(self.account.assigned_amount, 600000.0)
        self.assertEqual(self.account.held_amount, 0.0)

    def test_rejection_returns_balance(self):
        allocation = self.env['fund.allocation'].create({
            'fund_account_id': self.account.id,
            'expense_head_id': self.expense_head.id,
            'amount': 600000.0,
        })
        allocation.action_submit()
        allocation.action_reject()
        self.assertEqual(allocation.state, 'rejected')
        self.assertEqual(self.account.unassigned_balance, 1000000.0)

    def test_cannot_allocate_more_than_available(self):
        allocation = self.env['fund.allocation'].create({
            'fund_account_id': self.account.id,
            'expense_head_id': self.expense_head.id,
            'amount': 5000000.0,
        })
        with self.assertRaises(UserError):
            allocation.action_submit()
