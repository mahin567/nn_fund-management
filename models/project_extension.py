# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = 'project.project'

    total_allocated = fields.Monetary(
        string='Total Allocated Fund', compute='_compute_fund_balances', store=True,
        currency_field='currency_id')
    available_fund = fields.Monetary(
        string='Available Fund', compute='_compute_fund_balances', store=True,
        currency_field='currency_id')
    requisition_hold = fields.Monetary(
        string='Requisition Hold', compute='_compute_fund_balances', store=True,
        currency_field='currency_id')
    transfer_hold = fields.Monetary(
        string='Transfer Hold', compute='_compute_fund_balances', store=True,
        currency_field='currency_id')
    approved_unspent = fields.Monetary(
        string='Approved but Unspent', compute='_compute_fund_balances', store=True,
        currency_field='currency_id')
    total_spent = fields.Monetary(
        string='Total Spent', compute='_compute_fund_balances', store=True,
        currency_field='currency_id')
    incoming_transfers = fields.Monetary(
        string='Incoming Transfers', compute='_compute_fund_balances', store=True,
        currency_field='currency_id')
    outgoing_transfers = fields.Monetary(
        string='Outgoing Transfers', compute='_compute_fund_balances', store=True,
        currency_field='currency_id')

    fund_allocation_ids = fields.One2many(
        'fund.allocation', 'project_id', string='Fund Allocations')
    fund_requisition_ids = fields.One2many(
        'fund.requisition', 'project_id', string='Fund Requisitions')
    fund_transfer_in_ids = fields.One2many(
        'fund.transfer', 'destination_project_id', string='Transfers In')
    fund_transfer_out_ids = fields.One2many(
        'fund.transfer', 'source_project_id', string='Transfers Out')

    @api.depends(
        'fund_allocation_ids.amount', 'fund_allocation_ids.state',
        'fund_requisition_ids.amount', 'fund_requisition_ids.state',
        'fund_requisition_ids.billed_amount',
        'fund_transfer_in_ids.amount', 'fund_transfer_in_ids.state',
        'fund_transfer_out_ids.amount', 'fund_transfer_out_ids.state',
    )
    def _compute_fund_balances(self):
        for project in self:
            allocated = sum(project.fund_allocation_ids.filtered(
                lambda r: r.state == 'approved').mapped('amount'))

            req_hold = sum(project.fund_requisition_ids.filtered(
                lambda r: r.state in ('submitted', 'gm_approved')
            ).mapped('amount'))

            req_reserved = sum(project.fund_requisition_ids.filtered(
                lambda r: r.state == 'approved'
            ).mapped(lambda r: r.amount - r.billed_amount))

            spent = sum(project.fund_requisition_ids.mapped('billed_amount'))

            transfer_hold = sum(project.fund_transfer_out_ids.filtered(
                lambda r: r.state in ('submitted', 'gm_approved')
            ).mapped('amount'))

            incoming = sum(project.fund_transfer_in_ids.filtered(
                lambda r: r.state == 'approved').mapped('amount'))
            outgoing = sum(project.fund_transfer_out_ids.filtered(
                lambda r: r.state == 'approved').mapped('amount'))

            project.total_allocated = allocated
            project.requisition_hold = req_hold
            project.transfer_hold = transfer_hold
            project.total_spent = spent
            project.approved_unspent = req_reserved
            project.incoming_transfers = incoming
            project.outgoing_transfers = outgoing
            project.available_fund = (
                allocated + incoming - outgoing - req_hold
                - req_reserved - transfer_hold
            )
