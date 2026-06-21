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