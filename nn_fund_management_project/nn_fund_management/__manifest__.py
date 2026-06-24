# -*- coding: utf-8 -*-
{
    'name': 'NN Fund Management',
    'version': '17.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Fund management with dashboard, bank email integration, and configurable approval rules',
    'description': """
NN Fund Management
===================
Custom Odoo module to manage:

* Incoming funds and fund accounts
* Unassigned fund balances
* Project and expense-head allocations
* Fund requisitions
* Bills against approved requisitions
* Transfers between projects or expense heads
* GM and MD approval workflow with amount-based configurable rules
* Available, held, assigned and spent balances
* Full approval and transaction history
* Real-time dashboard (KPIs, charts, pending approvals)
* Bank email integration (BRAC, DBBL, IBBL, custom templates)
* Configurable approval routing by amount and transaction type
    """,
    'author': 'Your Name',
    'website': 'https://github.com/your-username/nn_fund_management',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'mail',
        'project',
        'web',
    ],

    'data': [
        # Security
        'security/fund_management_groups.xml',
        'security/ir.model.access.csv',
        'security/security_rules.xml',

        # Data
        'data/expense_head_data.xml',
        'data/sequence_data.xml',
        'data/bank_email_templates.xml',

        # Views
        'views/assets.xml',
        'views/dashboard_views.xml',
        'views/fund_account_views.xml',
        'views/incoming_fund_views.xml',
        'views/fund_allocation_views.xml',
        'views/fund_requisition_views.xml',
        'views/fund_bill_views.xml',
        'views/fund_transfer_views.xml',
        'views/expense_head_views.xml',
        'views/release_unused_funds_views.xml',
        'views/approval_rule_views.xml',
        'views/bank_email_views.xml',
        'views/menu_items.xml',
    ],

    'demo': [],

    'installable': True,
    'application': True,
    'auto_install': False,
}
