# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestFundTransfer(TransactionCase):

    def setUp(self):
        super().setUp()
        self.account = self.env['fund.account'].create({'name': 'Test Account'})
        incoming = self.env['fund.incoming'].create({
            'fund_account_id': self.account.id,
            'amount': 1000000.0,
            'transaction_reference': 'TXN-TRF-1',
        })
        incoming.action_confirm()

        self.head_a = self.env['fund.expense.head'].create({'name': 'Head A', 'code': 'TA'})
        self.head_b = self.env['fund.expense.head'].create({'name': 'Head B', 'code': 'TB'})

        gm_group = self.env.ref('nn_fund_management.group_gm_approver')
        md_group = self.env.ref('nn_fund_management.group_md_approver')
        self.env.user.write({'groups_id': [(4, gm_group.id), (4, md_group.id)]})

        alloc = self.env['fund.allocation'].create({
            'fund_account_id': self.account.id,
            'expense_head_id': self.head_a.id,
            'amount': 500000.0,
        })
        alloc.action_submit()
        alloc.action_gm_approve()
        alloc.action_md_approve()

    def test_transfer_same_source_destination_blocked(self):
        with self.assertRaises(ValidationError):
            self.env['fund.transfer'].create({
                'source_expense_head_id': self.head_a.id,
                'destination_expense_head_id': self.head_a.id,
                'amount': 1000.0,
            })

    def test_transfer_workflow_moves_balance(self):
        transfer = self.env['fund.transfer'].create({
            'source_expense_head_id': self.head_a.id,
            'destination_expense_head_id': self.head_b.id,
            'amount': 200000.0,
        })
        transfer.action_submit()
        self.assertEqual(self.head_a.transfer_hold, 200000.0)

        transfer.action_gm_approve()
        transfer.action_md_approve()
        self.assertEqual(transfer.state, 'approved')
        self.assertEqual(self.head_b.incoming_transfers, 200000.0)

    def test_transfer_exceeding_source_balance_blocked(self):
        transfer = self.env['fund.transfer'].create({
            'source_expense_head_id': self.head_a.id,
            'destination_expense_head_id': self.head_b.id,
            'amount': 9000000.0,
        })
        with self.assertRaises(UserError):
            transfer.action_submit()
