# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FundDashboard(models.Model):
    """Transient model that aggregates dashboard KPIs on demand.

    Not stored — all data is computed from live records each time the
    dashboard view is opened, so it always reflects real-time state.
    """
    _name = 'fund.dashboard'
    _description = 'Fund Management Dashboard'

    # KPI fields populated by _compute_kpis
    total_received = fields.Monetary(string='Total Received', currency_field='currency_id')
    total_unassigned = fields.Monetary(string='Unassigned Balance', currency_field='currency_id')
    total_held = fields.Monetary(string='On Hold', currency_field='currency_id')
    total_assigned = fields.Monetary(string='Total Assigned', currency_field='currency_id')
    total_spent = fields.Monetary(string='Total Spent', currency_field='currency_id')

    pending_allocations = fields.Integer(string='Pending Allocations')
    pending_requisitions = fields.Integer(string='Pending Requisitions')
    pending_transfers = fields.Integer(string='Pending Transfers')
    pending_verifications = fields.Integer(string='Pending Bank Verifications')

    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    @api.model
    def get_dashboard_data(self):
        """Return a dict of KPI values for the JS dashboard widget."""
        company = self.env.company
        currency = company.currency_id

        accounts = self.env['fund.account'].search([('company_id', '=', company.id)])

        total_received = sum(accounts.mapped('total_received'))
        total_unassigned = sum(accounts.mapped('unassigned_balance'))
        total_held = sum(accounts.mapped('held_amount'))
        total_assigned = sum(accounts.mapped('assigned_amount'))

        # Spending: sum of all posted bills
        total_spent = sum(
            self.env['fund.bill'].search([
                ('company_id', '=', company.id),
                ('state', '=', 'posted'),
            ]).mapped('amount')
        )

        # Pending approval counts
        pending_alloc = self.env['fund.allocation'].search_count([
            ('company_id', '=', company.id),
            ('state', 'in', ('submitted', 'gm_approved')),
        ])
        pending_req = self.env['fund.requisition'].search_count([
            ('company_id', '=', company.id),
            ('state', 'in', ('submitted', 'gm_approved')),
        ])
        pending_trf = self.env['fund.transfer'].search_count([
            ('company_id', '=', company.id),
            ('state', 'in', ('submitted', 'gm_approved')),
        ])
        pending_verify = self.env['fund.incoming'].search_count([
            ('company_id', '=', company.id),
            ('state', '=', 'pending_verification'),
        ])

        # Top projects by available fund (top 5)
        projects = self.env['project.project'].search(
            [('available_fund', '>', 0)], order='available_fund desc', limit=5)
        top_projects = [
            {
                'name': p.name,
                'available': p.available_fund,
                'spent': p.total_spent,
                'allocated': p.total_allocated,
            }
            for p in projects
        ]

        # Top expense heads by available fund (top 5)
        heads = self.env['fund.expense.head'].search(
            [('available_fund', '>', 0), ('company_id', '=', company.id)],
            order='available_fund desc', limit=5)
        top_heads = [
            {
                'name': h.name,
                'available': h.available_fund,
                'spent': h.total_spent,
                'allocated': h.total_allocated,
            }
            for h in heads
        ]

        # Recent approval history (last 10 entries)
        recent_history = self.env['fund.approval.history'].search(
            [], order='create_date desc', limit=10)
        recent_activity = [
            {
                'action': dict(
                    self.env['fund.approval.history']._fields['approval_level'].selection
                ).get(h.approval_level, h.approval_level),
                'actor': h.actor_id.name,
                'amount': h.amount,
                'date': h.action_date.strftime('%Y-%m-%d %H:%M') if h.action_date else '',
                'comment': h.comment or '',
            }
            for h in recent_history
        ]

        # Monthly incoming funds (last 6 months) for the sparkline chart
        self.env.cr.execute("""
            SELECT
                TO_CHAR(date, 'Mon YYYY') AS month,
                DATE_TRUNC('month', date) AS month_start,
                SUM(amount) AS total
            FROM fund_incoming
            WHERE state = 'confirmed'
              AND company_id = %s
              AND date >= DATE_TRUNC('month', NOW()) - INTERVAL '5 months'
            GROUP BY month, month_start
            ORDER BY month_start
        """, (company.id,))
        monthly_incoming = [
            {'month': row[0], 'total': float(row[2])}
            for row in self.env.cr.fetchall()
        ]

        return {
            'currency_symbol': currency.symbol,
            'currency_position': currency.position,
            'total_received': total_received,
            'total_unassigned': total_unassigned,
            'total_held': total_held,
            'total_assigned': total_assigned,
            'total_spent': total_spent,
            'pending_allocations': pending_alloc,
            'pending_requisitions': pending_req,
            'pending_transfers': pending_trf,
            'pending_verifications': pending_verify,
            'top_projects': top_projects,
            'top_expense_heads': top_heads,
            'recent_activity': recent_activity,
            'monthly_incoming': monthly_incoming,
        }
