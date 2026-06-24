# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestFundAccount(TransactionCase):

    def setUp(self):
        super().setUp()
        self.account = self.env['fund.account'].create({
            'name': 'Test Bank Account',
            'account_type': 'bank',
        })

    def test_initial_balances_are_zero(self):
        self.assertEqual(self.account.total_received, 0.0)
        self.assertEqual(self.account.unassigned_balance, 0.0)

    def test_confirmed_incoming_increases_unassigned_balance(self):
        incoming = self.env['fund.incoming'].create({
            'fund_account_id': self.account.id,
            'amount': 1000000.0,
            'transaction_reference': 'TXN-001',
        })
        incoming.action_confirm()
        self.assertEqual(self.account.total_received, 1000000.0)
        self.assertEqual(self.account.unassigned_balance, 1000000.0)

    def test_draft_incoming_does_not_affect_balance(self):
        self.env['fund.incoming'].create({
            'fund_account_id': self.account.id,
            'amount': 500000.0,
            'transaction_reference': 'TXN-002',
        })
        self.assertEqual(self.account.unassigned_balance, 0.0)

    def test_duplicate_transaction_reference_blocked(self):
        self.env['fund.incoming'].create({
            'fund_account_id': self.account.id,
            'amount': 1000.0,
            'transaction_reference': 'DUP-REF',
        })
        with self.assertRaises(Exception):
            self.env['fund.incoming'].create({
                'fund_account_id': self.account.id,
                'amount': 2000.0,
                'transaction_reference': 'DUP-REF',
            })
