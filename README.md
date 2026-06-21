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
Requirements

System

DependencyVersionDocker24.x or laterDocker Composev2.x or laterGitAny recent version

Python (inside the container)

All Python dependencies are handled by the base Odoo Docker image. No additional pip install is required.

Odoo Dependencies (declared in __manifest__.py)

python'depends': ['base', 'mail', 'account']


Installation

Option 1 — Docker (Recommended)

See the Docker Setup section below.

Option 2 — Manual (existing Odoo instance)


Clone this repository into your Odoo addons directory:


bashgit clonehttps://github.com/mahin567/nn_fund-management /path/to/odoo/addons/nn_fund_management


Restart the Odoo service:


bashsudo systemctl restart odoo
# or
./odoo-bin --addons-path=addons -d your_database -u nn_fund_management


In Odoo, go to Settings → Apps, search for nn_fund_management, and click Install.



Docker Setup

The project ships with a ready-to-use Docker Compose configuration.

Files

nn_fund_management/
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── odoo.conf
├── nn_fund_management/        ← the Odoo module
│   ├── __manifest__.py
│   └── ...
└── README.md

Step 1 — Clone the repository

bashgit clone https://github.com/mahin567/nn_fund-management
cd nn_fund_management

Step 2 — Start the containers

bashdocker compose -f docker/docker-compose.yml up -d

This starts:


odoo — Odoo 17 on port 8069
db — PostgreSQL 15 on port 5432


Step 3 — Create the database and install the module

Open your browser at http://localhost:8069 and complete the database creation form. Then:


Go to Settings → Apps → Update Apps List
Search for Fund Management
Click Install


Or install via CLI:

bashdocker compose -f docker/docker-compose.yml exec odoo \
  odoo --addons-path=/mnt/extra-addons -d odoo -i nn_fund_management --stop-after-init

Step 4 — Stop the containers

bashdocker compose -f docker/docker-compose.yml down

To also remove volumes (full reset):

bashdocker compose -f docker/docker-compose.yml down -v

Configuration

1. Assign Security Groups

After installation, assign users to the appropriate groups under Settings → Users → [select user] → Access Rights:

GroupPurposeFund UserCreate and view fund requestsFinance UserConfirm incoming funds; view financial recordsGM ApproverApprove/reject at the GM levelMD ApproverApprove/reject at the MD levelFund AdministratorFull access; cancel approved transactions

2. Configure Approvers

Go to Fund Management → Configuration → Approval Settings and assign specific users (or groups) as GM Approver and MD Approver. These are not hardcoded — they can be changed at any time.

3. Create Fund Accounts

Go to Fund Management → Fund Accounts → New and create at least one account (bank or cash) before recording incoming funds.

4. Create Expense Heads (optional)

Go to Fund Management → Configuration → Expense Heads to create categories such as Office Rent, Salary, Utilities, etc.


Testing

Run Automated Tests

bashdocker compose -f docker/docker-compose.yml exec odoo \
  odoo -d odoo --test-enable --stop-after-init -i nn_fund_management

Manual Demo Scenario

Follow these steps to verify all core features end-to-end:


Receive BDT 1,000,000 in a fund account.
Allocate BDT 600,000 to Project A — confirm it goes on hold.
Reject the allocation — confirm the balance returns to unassigned.
Re-submit and approve the allocation.
Transfer BDT 200,000 from Project A to Project B — confirm transfer hold.
Approve the transfer.
Create a BDT 150,000 requisition for Project B and approve it.
Post a BDT 100,000 partial bill — confirm BDT 50,000 remains billable.
Try to post a BDT 60,000 bill — confirm the system blocks it.
Try to use Project B's requisition for Project A — confirm the system blocks it.



Architecture

Module Structure

nn_fund_management/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── fund_account.py          # Fund accounts and balance tracking
│   ├── incoming_fund.py         # Incoming fund records
│   ├── fund_allocation.py       # Allocation requests (project/expense head)
│   ├── fund_requisition.py      # Requisition requests
│   ├── fund_bill.py             # Bills against requisitions
│   ├── fund_transfer.py         # Transfer requests
│   ├── approval_history.py      # Immutable approval/action log
│   └── project_expense_balance.py  # Computed balances per project/expense head
├── views/
│   ├── fund_account_views.xml
│   ├── incoming_fund_views.xml
│   ├── fund_allocation_views.xml
│   ├── fund_requisition_views.xml
│   ├── fund_bill_views.xml
│   ├── fund_transfer_views.xml
│   └── menu_items.xml
├── security/
│   ├── ir.model.access.csv      # ACLs per model per group
│   └── security_rules.xml       # Record rules (multi-company, ownership)
├── data/
│   └── expense_heads_data.xml   # Default expense head categories
├── tests/
│   ├── test_fund_account.py
│   ├── test_allocation.py
│   ├── test_requisition.py
│   ├── test_transfer.py
│   └── test_bill_control.py
└── wizards/
    └── release_unused_funds.py  # Wizard to close requisitions and release unused amounts

Key Design Decisions

Balance integrity — All balance fields on fund.account and project/expense records are compute fields stored in the database (store=True). They are recalculated on every relevant write. No direct SQL writes to balance columns anywhere in user-facing code.

Hold mechanism — When a request is submitted, the requested amount is immediately subtracted from the available balance and added to a hold bucket on the parent account or project. This prevents the same money being used twice even before approval completes.

Approval sequencing — A state machine enforces draft → submitted → gm_approved → md_approved → approved. The MD approval button is only active after GM approval is recorded. Server-side _check_approval_rights() re-validates the current user regardless of UI button visibility.

Audit log — Every state transition writes an immutable fund.approval.history record (no unlink allowed for Finance/GM/MD groups). The log captures actor, previous state, new state, timestamp, comment, and amounts.

Double-spend prevention — SQL-level constraints (CHECK constraints and UNIQUE constraints on transaction references per account) back up the ORM-level checks.


Assumptions


The module targets Odoo 17 Community Edition. Enterprise-only features (e.g. approval studio) are not used.
A "project" refers to Odoo's built-in project.project model. If the Project module is not installed, a lightweight internal project model is used instead.
Currency is assumed to be BDT by default but follows the company currency configured in Odoo settings.
The two approval levels (GM, MD) are the minimum. The bonus configurable approval rules feature extends this.
Bill integration uses a custom bill model (fund.bill) rather than Odoo Vendor Bills, to keep the module self-contained and avoid account module dependency issues during testing.
Multi-company record isolation uses Odoo's built-in company_id field and record rules — no custom sharding logic.



Known Limitations


Bank email integration is a prototype. It parses common Bangladesh bank notification email formats (BRAC, Dutch-Bangla, Islami Bank) but may not cover all templates without further customization.
Dashboard uses Odoo's built-in dashboard view; real-time websocket push is not implemented — data refreshes on page load.
The bill reversal flow cancels the bill record internally; it does not integrate with Odoo's journal entry reversal if account module journal entries have already been posted.
Approval rules for amount-based thresholds (bonus feature) only apply to new requests created after the rule is configured — existing draft requests are not retroactively reassigned.
The module has been tested on Linux (Ubuntu 22.04) and macOS (Apple Silicon via Rosetta). Windows Docker Desktop should work but has not been formally tested.
Automated tests cover core balance logic and approval workflows. UI-level (tour) tests are not included.