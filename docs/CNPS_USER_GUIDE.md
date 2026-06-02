# CNPS User Guide

## Overview

The **CNPS Smart Automated Analytics System** supports institutional analytics for the Caisse Nationale de Prévoyance Sociale (CNPS):

- **Continuous monitoring** — scheduled data refresh, KPIs, anomalies, forecasts
- **Goal-driven analysis** — specify what to compute each time you analyze
- **CNPS presets** — contributions, pensions, AT/MP, employer compliance, regional performance

## Roles

| System role | CNPS title | Capabilities |
|-------------|------------|--------------|
| admin | IT Administrator | Governance, all units, user management |
| manager | Contribution Manager / Pension Officer / AT/MP Analyst | Analysis, data refresh, settings |
| viewer | Institutional Statistician | Read-only dashboard and reports |

## Quick start (demo)

1. Generate sample data: `python scripts/seed_cnps_sample.py`
2. Sign in as a manager.
3. **Settings** → connect SQLite: `sqlite:///…/cnps_institutional_sample.db`
4. **Dashboard** → **Refresh Data** (ETL monitoring).
5. **Analysis** → pick a CNPS preset or enter a custom goal.

## Goal-driven analysis

Unlike generic BI tools that only auto-sum tables, this system requires an **analysis goal**:

- Natural language: *"Monthly contribution collection rate by regional office"*
- Formula (optional): `total_paid / total_expected`
- CNPS preset: one-click templates aligned to social security operations

Results are stored in **Analysis history** and can feed dashboards and custom reports.

## Reports

| Report type | Use case |
|-------------|----------|
| Executive Brief | Leadership summary |
| Custom Report | User-defined scope and CNPS sections |
| Report History | Past AI-generated briefings |

## Admin governance

- **Governance** → Overview: cross-unit KPIs and institutional timeline
- **Departments**: organizational units linked to regional offices
- **Semantic layer**: CNPS Core Schema field mappings
- **Institutional Report**: combined multi-unit view (admin overview)

## Exports

- KPI CSV: `GET /api/kpis/export`
- Analysis runs CSV: `GET /api/analysis/runs/export`

## Database migrations

Run in Supabase SQL Editor (in order):

1. Existing migrations `001`–`009`
2. [`010_analysis_goals.sql`](../backend/migrations/010_analysis_goals.sql)
3. [`011_cnps_kpi_seed.sql`](../backend/migrations/011_cnps_kpi_seed.sql)
4. [`012_org_hierarchy.sql`](../backend/migrations/012_org_hierarchy.sql)

## Environment

Copy [`backend/.env.cnps.example`](../backend/.env.cnps.example) values into your `.env` for CNPS branding and email sender configuration.
