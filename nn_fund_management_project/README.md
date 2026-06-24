# nn_fund_management

Custom Odoo module for end-to-end fund management — incoming funds, allocations, requisitions, bills, transfers, and multi-level approvals.

---

## Table of Contents

1. [Odoo Version](#odoo-version)
2. [Module Overview](#module-overview)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Docker Setup](#docker-setup)
6. [Configuration](#configuration)
7. [Testing](#testing)
8. [Architecture](#architecture)
9. [Assumptions](#assumptions)
10. [Known Limitations](#known-limitations)

---

## Odoo Version

Odoo 17.0 (Community Edition)

---

## Module Overview

`nn_fund_management` provides:

- **Fund Accounts** — track unassigned, held, and assigned balances across bank/cash accounts
- **Incoming Funds** — record and confirm fund receipts with deduplication on transaction references
- **Fund Allocation** — assign unassigned funds to projects or expense heads
- **Fund Requisition** — request funds from a project or expense head for spending
- **Bill Control** — link bills to approved requisitions; enforce remaining billable amounts
- **Fund Transfer** — move funds between projects and/or expense heads
- **Two-Level Approval** — GM → MD workflow for allocations, requisitions, and transfers
- **Audit History** — immutable log of every financial action
- **Access Control** — role-based groups with server-side enforcement
- **Dashboard** — real-time KPIs, charts, and pending approval counts
- **Bank Email Integration** — auto-parse BRAC, DBBL, and IBBL notification emails into draft incoming fund records
- **Configurable Approval Rules** — amount-based routing rules that can skip or pin approval levels

---

## Requirements

### System

| Dependency     | Version          |
|----------------|------------------|
| Docker         | 24.x or later    |
| Docker Compose | v2.x or later    |
| Git            | Any recent version |

### Python (inside the container)

All Python dependencies are handled by the base Odoo Docker image. No additional `pip install` is required.

### Odoo Dependencies (declared in `__manifest__.py`)

```python
'depends': ['base', 'mail', 'project', 'web']
```

---

## Installation

### Option 1 — Docker (Recommended)

See the [Docker Setup](#docker-setup) section below.

### Option 2 — Manual (existing Odoo instance)

1. Clone this repository into your Odoo addons directory:

```bash
git clone https://github.com/mahin567/nn_fund-management /path/to/odoo/addons/nn_fund_management
```

2. Restart the Odoo service:

```bash
sudo systemctl restart odoo
# or
./odoo-bin --addons-path=addons -d your_database -u nn_fund_management
```

3. In Odoo, go to **Settings → Apps**, search for `nn_fund_management`, and click **Install**.

---

## Docker Setup

The project ships with a ready-to-use Docker Compose configuration.

### Files

```
nn_fund_management_project/
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── odoo.conf
├── nn_fund_management/        ← the Odoo module
│   ├── __manifest__.py
│   └── ...
└── README.md
```

### Step 1 — Clone the repository

```bash
git clone https://github.com/mahin567/nn_fund-management
cd nn_fund_management_project
```

### Step 2 — Download Chart.js (required for dashboard)

```bash
mkdir -p nn_fund_management/static/lib/chartjs
curl -L https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js \
     -o nn_fund_management/static/lib/chartjs/chart.umd.min.js
```

### Step 3 — Start the containers

```bash
docker compose -f docker/docker-compose.yml up -d
```

This starts:

- `odoo` — Odoo 17 on port 8069
- `db` — PostgreSQL 15 on port 5432

### Step 4 — Create the database and install the module

Open your browser at `http://localhost:8069` and complete the database creation form. Then:

- Go to **Settings → Apps → Update Apps List**
- Search for **Fund Management**
- Click **Install**

Or install via CLI:

```bash
docker compose -f docker/docker-compose.yml exec odoo \
  odoo --addons-path=/mnt/extra-addons -d odoo -i nn_fund_management --stop-after-init
```

### Step 5 — Stop the containers

```bash
docker compose -f docker/docker-compose.yml down
```

To also remove volumes (full reset):

```bash
docker compose -f docker/docker-compose.yml down -v
```

---

## Configuration

### 1. Assign Security Groups

After installation, assign users to the appropriate groups under **Settings → Users → [select user] → Access Rights**:

| Group               | Purpose                                          |
|---------------------|--------------------------------------------------|
| Fund User           | Create and view fund requests                    |
| Finance User        | Confirm incoming funds; view financial records   |
| GM Approver         | Approve/reject at the GM level                   |
| MD Approver         | Approve/reject at the MD level                   |
| Fund Administrator  | Full access; cancel approved transactions        |

### 2. Configure Approvers

Go to **Fund Management → Configuration → Approval Settings** and assign specific users (or groups) as GM Approver and MD Approver. These are not hardcoded — they can be changed at any time.

### 3. Create Fund Accounts

Go to **Fund Management → Fund Accounts → New** and create at least one account (bank or cash) before recording incoming funds.

### 4. Create Expense Heads (optional)

Go to **Fund Management → Configuration → Expense Heads** to create categories such as Office Rent, Salary, Utilities, etc.

---

## Testing

### Run Automated Tests

```bash
docker compose -f docker/docker-compose.yml exec odoo \
  odoo -d odoo --test-enable --stop-after-init -i nn_fund_management
```

### Manual Demo Scenario

Follow these steps to verify all core features end-to-end:

1. Receive BDT 1,000,000 in a fund account.
2. Allocate BDT 600,000 to Project A — confirm it goes on hold.
3. Reject the allocation — confirm the balance returns to unassigned.
4. Re-submit and approve the allocation.
5. Transfer BDT 200,000 from Project A to Project B — confirm transfer hold.
6. Approve the transfer.
7. Create a BDT 150,000 requisition for Project B and approve it.
8. Post a BDT 100,000 partial bill — confirm BDT 50,000 remains billable.
9. Try to post a BDT 60,000 bill — confirm the system blocks it.
10. Try to use Project B's requisition for Project A — confirm the system blocks it.

---

## Architecture

### Module Structure

```
nn_fund_management/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── approval_history.py       # Immutable audit log (append-only)
│   ├── approval_mixin.py         # Shared GM→MD state machine (abstract)
│   ├── approval_rule.py          # Configurable amount-based routing rules
│   ├── fund_account.py           # Bank/cash accounts and balance tracking
│   ├── expense_head.py           # Expense categories with fund balances
│   ├── project_extension.py      # Adds fund fields to project.project
│   ├── fund_incoming.py          # Incoming fund records and confirmation
│   ├── fund_allocation.py        # Allocation requests (project/expense head)
│   ├── fund_requisition.py       # Requisition requests
│   ├── fund_bill.py              # Bills against requisitions
│   ├── fund_transfer.py          # Transfer requests
│   ├── bank_email.py             # Bank email parsing and auto-draft creation
│   └── dashboard.py              # KPI aggregation for JS dashboard
├── views/
│   ├── assets.xml                # Register JS/CSS in Odoo asset bundle
│   ├── dashboard_views.xml
│   ├── fund_account_views.xml
│   ├── incoming_fund_views.xml
│   ├── fund_allocation_views.xml
│   ├── fund_requisition_views.xml
│   ├── fund_bill_views.xml
│   ├── fund_transfer_views.xml
│   ├── expense_head_views.xml
│   ├── approval_rule_views.xml
│   ├── bank_email_views.xml
│   ├── release_unused_funds_views.xml
│   └── menu_items.xml
├── security/
│   ├── fund_management_groups.xml  # Defines 5 user groups
│   ├── ir.model.access.csv         # ACLs per model per group
│   └── security_rules.xml          # Multi-company record isolation rules
├── data/
│   ├── expense_head_data.xml        # Seed expense head categories
│   ├── sequence_data.xml            # Auto-increment reference sequences
│   └── bank_email_templates.xml     # BRAC, DBBL, IBBL regex templates
├── static/
│   ├── lib/chartjs/chart.umd.min.js
│   └── src/
│       ├── css/fund_dashboard.css
│       ├── js/fund_dashboard.js
│       └── xml/fund_dashboard.xml
├── tests/
│   ├── test_fund_account.py
│   ├── test_allocation.py
│   ├── test_requisition.py
│   ├── test_transfer.py
│   └── test_bill_control.py
└── wizerds/
    └── release_unused_funds.py  # Wizard to close requisitions and release unused amounts
```

### Money Flow

```
Bank Email ──► Incoming Fund ──► Fund Account (unassigned_balance)
                                        │
                                   Allocation  ──► (held) ──► (approved)
                                        │
                              Project / Expense Head (available_fund)
                                    │           │
                               Requisition   Transfer ──► other Project
                                    │
                                  Bill (posted against requisition)
                                    │
                            Approval History (immutable audit log)
```

### Approval State Machine

All three transaction models (`fund.allocation`, `fund.requisition`, `fund.transfer`) share the same state machine via `fund.approval.mixin`:

```
draft ──► submitted ──► gm_approved ──► approved
                  └──► rejected
          └──► cancelled (admin or own draft only)
```

| Transition            | Method               | Who                        |
|-----------------------|----------------------|----------------------------|
| draft → submitted     | `action_submit()`    | Fund User                  |
| submitted → gm_approved | `action_gm_approve()` | GM Approver             |
| gm_approved → approved | `action_md_approve()` | MD Approver              |
| submitted/gm_approved → rejected | `action_reject()` | GM or MD Approver |
| any → cancelled       | `action_cancel()`    | Fund Admin or own draft    |

If a matching `fund.approval.rule` has `require_gm=False`, submission jumps directly to `gm_approved`. If `require_md=False`, GM approval is the final step.

### Balance Design

All balance fields are `store=True` computed fields. No code ever writes to a balance column directly — balances recalculate automatically when the state of a related record changes.

**Fund Account (`fund.account`)**

| Field                | Formula                                              |
|----------------------|------------------------------------------------------|
| `total_received`     | SUM(incoming.amount) where state = confirmed         |
| `held_amount`        | SUM(allocation.amount) where state in (submitted, gm_approved) |
| `assigned_amount`    | SUM(allocation.amount) where state = approved        |
| `unassigned_balance` | total_received − held_amount − assigned_amount       |

**Project / Expense Head**

| Field                | Formula                                              |
|----------------------|------------------------------------------------------|
| `total_allocated`    | SUM(allocation.amount) where state = approved        |
| `requisition_hold`   | SUM(requisition.amount) where state in (submitted, gm_approved) |
| `approved_unspent`   | SUM(requisition.amount − billed_amount) where state = approved |
| `total_spent`        | SUM(requisition.billed_amount)                       |
| `transfer_hold`      | SUM(transfer_out.amount) where state in (submitted, gm_approved) |
| `incoming_transfers` | SUM(transfer_in.amount) where state = approved       |
| `outgoing_transfers` | SUM(transfer_out.amount) where state = approved      |
| `available_fund`     | total_allocated + incoming − outgoing − req_hold − approved_unspent − transfer_hold |

### Key Design Decisions

**Balance integrity** — All balance fields are computed and stored. They recalculate on every relevant write. No direct writes to balance columns anywhere in user-facing code.

**Hold mechanism** — When a request is submitted, the requested amount is immediately moved into a hold bucket on the parent account or project. This prevents the same money being used twice even before approval completes.

**Approval sequencing** — The state machine enforces `draft → submitted → gm_approved → approved`. The MD approval button is only active after GM approval is recorded. Server-side `_check_approval_rights()` re-validates the current user regardless of UI button visibility.

**Rule resolved at submission** — The matching `fund.approval.rule` is resolved once and stored in `applied_rule_id` at submission time. Changing rules after submission does not affect in-flight requests.

**Audit log** — Every state transition writes an immutable `fund.approval.history` record. Both `write()` and `unlink()` raise `UserError` on this model — records are strictly append-only.

**Double-spend prevention** — SQL-level `CHECK` constraints and `UNIQUE` constraints on transaction references back up the ORM-level checks.

**Self-contained** — `fund.bill` is a custom model rather than an Odoo vendor bill, so the module installs on a base Odoo instance without requiring the `account` module.

---

## Assumptions

- The module targets Odoo 17 Community Edition. Enterprise-only features (e.g. approval studio) are not used.
- A "project" refers to Odoo's built-in `project.project` model.
- Currency follows the company currency configured in Odoo settings (defaults to BDT).
- The two approval levels (GM, MD) are the minimum. Configurable approval rules extend this.
- Multi-company record isolation uses Odoo's built-in `company_id` field and record rules — no custom sharding logic.

---

## Known Limitations

- **Bank email integration** is a prototype. It parses common Bangladesh bank notification email formats (BRAC, Dutch-Bangla, Islami Bank) but may not cover all templates without further customisation.
- **Dashboard** data refreshes on page load — real-time websocket push is not implemented.
- **Bill reversal** cancels the bill record internally; it does not integrate with Odoo's journal entry reversal if account module journal entries have already been posted.
- **Approval rules** only apply to new requests created after the rule is configured — existing draft requests are not retroactively reassigned.
- The module has been tested on Linux (Ubuntu 22.04) and macOS (Apple Silicon via Rosetta). Windows Docker Desktop should work but has not been formally tested.
- Automated tests cover core balance logic and approval workflows. UI-level (tour) tests are not included.

