# -*- coding: utf-8 -*-
{
    'name': 'NN Fund Management',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Manage incoming funds, allocations, requisitions, bills, '
                'transfers and multi-level approvals',
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
* GM and MD approval workflow
* Available, held, assigned and spent balances
* Full approval and transaction history

Built to ensure the same money cannot be allocated, transferred,
or spent more than once.
    """,
    'author': 'Your Name',
    'website': 'https://github.com/your-username/nn_fund_management',
    'license': 'LGPL-3',

    # Odoo modules this module depends on
    'depends': [
        'base',
        'mail',
        'project',
    ],

    # Files loaded on module install/update, in order
    'data': [
        # Security (load groups/access before views that reference them)
        'security/fund_management_groups.xml',
        'security/ir.model.access.csv',
        'security/security_rules.xml',

        # Data
        'data/expense_head_data.xml',
        'data/sequence_data.xml',

        # Views
        'views/fund_account_views.xml',
        'views/incoming_fund_views.xml',
        'views/fund_allocation_views.xml',
        'views/fund_requisition_views.xml',
        'views/fund_bill_views.xml',
        'views/fund_transfer_views.xml',
        'views/expense_head_views.xml',
        'views/menu_items.xml',
    ],

    # Demo data, only loaded if demo mode is enabled
    'demo': [],

    'installable': True,
    'application': True,
    'auto_install': False,
}
