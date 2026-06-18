**nn_fund_management

Custom Odoo module for end-to-end fund management — incoming funds, allocations, requisitions, bills, transfers, and multi-level approvals.


Table of Contents


1.Odoo Version
2.Module Overview
3.Requirements
4.Installation
5.Docker Setup
6.Configuration
7.Testing
8.Architecture
9.Assumptions
10.Known Limitations



**Odoo Version

  Odoo 17.0 (Community Edition)


**Module Overview

   nn_fund_management provides:


Fund Accounts — track unassigned, held, and assigned balances across bank/cash accounts
Incoming Funds — record and confirm fund receipts with deduplication on transaction references
Fund Allocation — assign unassigned funds to projects or expense heads
Fund Requisition — request funds from a project or expense head for spending
Bill Control — link bills to approved requisitions; enforce remaining billable amounts
Fund Transfer — move funds between projects and/or expense heads
Two-Level Approval — GM → MD workflow for allocations, requisitions, and transfers
Audit History — immutable log of every financial action
Access Control — role-based groups with server-side enforcement



Requirements

System

DependencyVersionDocker24.x or laterDocker Composev2.x or laterGitAny recent version
