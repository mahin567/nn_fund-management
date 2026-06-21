# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestFundBillControl(TransactionCase):

    def setUp(self):
        super().setUp()
        self.account = self.env['fund.account'].create({'name': 'Test Account'})
        incoming = self.env['fund.incoming'].create({
            'fund_account_id': self.account.id,
            'amount': 1000000.0,
            'transaction_reference': 'TXN-BILL-1',
        })
        incoming.action_confirm()

        self.head_a = self.env['fund.expense.head'].create({'name': 'Head A', 'code': 'HA'})
        self.head_b = self.env['fund.expense.head'].create({'name': 'Head B', 'code': 'HB'})

        gm_group = self.env.ref('nn_fund_management.group_gm_approver')
        md_group = self.env.ref('nn_fund_management.group_md_approver')
        admin_group = self.env.ref('nn_fund_management.group_fund_admin')
        self.env.user.write({'groups_id': [(4, gm_group.id), (4, md_group.id), (4, admin_group.id)]})

        alloc_b = self.env['fund.allocation'].create({
            'fund_account_id': self.account.id,
            'expense_head_id': self.head_b.id,
            'amount': 500000.0,
        })
        alloc_b.action_submit()
        alloc_b.action_gm_approve()
        alloc_b.action_md_approve()

        self.req_b = self.env['fund.requisition'].create({
            'expense_head_id': self.head_b.id,
            'amount': 150000.0,
        })
        self.req_b.action_submit()
        self.req_b.action_gm_approve()
        self.req_b.action_md_approve()

    def test_partial_bill_then_block_overage(self):
        bill1 = self.env['fund.bill'].create({
            'requisition_id': self.req_b.id,
            'amount': 100000.0,
        })
        bill1.action_post()
        self.assertEqual(self.req_b.remaining_billable, 50000.0)

        bill2 = self.env['fund.bill'].create({
            'requisition_id': self.req_b.id,
            'amount': 60000.0,
        })
        with self.assertRaises(UserError):
            bill2.action_post()

    def test_bill_reversal_restores_billable(self):
        bill = self.env['fund.bill'].create({
            'requisition_id': self.req_b.id,
            'amount': 100000.0,
        })
        bill.action_post()
        self.assertEqual(self.req_b.remaining_billable, 50000.0)
        bill.action_cancel()
        self.assertEqual(self.req_b.remaining_billable, 150000.0)

    def test_requisition_cross_use_blocked_at_data_level(self):
        # req_b.expense_head_id is Head B; project_id/expense_head_id on the bill
        # are related fields copied from the requisition, so a bill is always
        # tied to the same target as its requisition by construction.
        bill = self.env['fund.bill'].create({
            'requisition_id': self.req_b.id,
            'amount': 1000.0,
        })
        self.assertEqual(bill.expense_head_id, self.head_b)
        self.assertNotEqual(bill.expense_head_id, self.head_a)
