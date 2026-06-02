# CNPS Full Demo — Square-One Testing Guide

Use database file **`cnps_full_demo.db`** (generate with `python scripts/seed_cnps_full_demo.py`) to exercise every major feature by role.

---

## Part A — Your questions answered

### 1. Purple highlights on discovered tables (Schema Explorer)

Those pills use color **`#a78bfa` (purple/violet)** in [`SchemaExplorer.jsx`](../frontend/src/pages/SchemaExplorer.jsx).

| Purple pill on… | Meaning |
|-----------------|--------|
| **Table row** | **Business domain classification** — automatic labels from table/column names (EN + FR keywords). Examples: `contribution`, `payment`, `pension`, `claim`, `employer`, `beneficiary`. |
| **Column row** | Tag **`id`** — column name looks like an identifier (`id`, `employee_id`, `code`, etc.). |

Other colors (not purple):

| Color | Tag | Meaning |
|-------|-----|--------|
| Cyan | `view` | Database view (not a base table) |
| Cyan | `date` | Column used as a date for time-series analysis |
| Yellow | `amount` | Monetary/numeric aggregate column |
| Green | `PK` | Primary key |

Logic lives in [`schema_introspector.py`](../backend/api/services/schema_introspector.py) (`DOMAIN_KEYWORDS`, `_classify_table()`). No manual setup required — introspection only.

---

### 2. Analysis presets (Analysis page) — who creates them?

| Aspect | Detail |
|--------|--------|
| **Today** | Presets are **seeded in Supabase** by migration [`010_analysis_goals.sql`](../backend/migrations/010_analysis_goals.sql) into table `cnps_analysis_presets`. |
| **Who** | Effectively **IT Administrator** (runs migrations / could insert SQL in Supabase). |
| **End users** | Managers pick a preset card; it fills the goal text and runs analysis. |
| **Custom goals** | Any manager can type a **natural-language goal** or optional **formula** without using a preset. |

**Can users create presets?**

- **In the UI today:** No dedicated “Create preset” screen yet.
- **Ways to add presets now:**
  1. Supabase SQL Editor — `INSERT INTO cnps_analysis_presets (...)`  
  2. Admin API (if enabled): `POST /api/analysis/admin/presets` — see below.

Preset examples shipped: Contributions Monitoring, Pension Analytics, Workplace Accident Analytics, Employer Compliance, Regional Performance.

---

### 3. “Ready to run” analyses (Schema Explorer) — from KPIs?

**No — they are not driven by declared KPIs or semantic templates.**

They are built by **`suggest_analyses()`** in [`schema_introspector.py`](../backend/api/services/schema_introspector.py):

1. Introspect connected DB → classify each table (purple domains).
2. **Rule catalog** per domain, e.g.:
   - `contribution` tables → contribution trend, late/missing detection  
   - `payment` tables → payment anomaly (z-score)  
   - `claim` tables → claim throughput over time  
   - `pension` / `benefit` → liability-style forecast  
3. Plus generic **table overview** cards for largest tables.

Running one executes a fixed **`kind`** (`time_series_sum`, `anomaly_zscore`, etc.) on the chosen table/columns — then you can **Sync to dashboard** to push results into KPIs.

**Declared KPIs** (Admin → Semantic layer) affect:

- ETL when mappings exist (`configured` mode)  
- Validation (required fields)  
- **Not** which cards appear in “Ready to run analyses”

**Goal-driven Analysis** (`/analysis`) is separate: user/preset **goal text** → `analysis_engine` → SQL/NLQ.

---

### 4. Other databases (Oracle, MySQL, PostgreSQL, etc.)

**Yes.** The backend supports:

| Engine | Connection notes |
|--------|------------------|
| **SQLite** | `sqlite:///C:/path/to/cnps_full_demo.db` — best for local demo |
| **PostgreSQL** | `postgresql://user:pass@host:5432/dbname` |
| **MySQL / MariaDB** | `mysql://user:pass@host:3306/dbname` |
| **Oracle** | `oracle+oracledb://user:pass@host:1521/?service_name=X` (needs `oracledb` in requirements) |
| **SQL Server** | `mssql+pymssql://...` |
| **MongoDB** | Document path for NLQ; not for full ETL KPI pipeline |

Use **Settings → Database type** and connection URI. SSH tunnel supported for remote DBs.

To use **PostgreSQL/Oracle** with the same demo data: load `cnps_full_demo.db` schema via your tool, or ask for a future `pg_dump` script.

---

## Part B — Generate the full demo database

```bash
cd C:\Users\nguki\OneDrive\Desktop\SAAS
python scripts/seed_cnps_full_demo.py
```

Output: **`cnps_full_demo.db`** (~3k+ contribution rows, 8 regions, 17 employers, AT/MP claims, pensions, benefits).

**Built-in test scenarios:**

| Scenario | Where in data |
|----------|----------------|
| Delinquent employer | `EMP-1016` — many `overdue` contributions |
| Regional gap | `MAR` — sparse last months (validation warning) |
| Duplicate contribution | Same `employee_id` + `period_month` twice |
| AT/MP claims | `at_mp_claims` table |
| Pension trends | `pension_payments` |
| Multi-region | 8 `regional_offices` |

**Connection string (Settings):**

```
sqlite:///C:/Users/nguki/OneDrive/Desktop/SAAS/cnps_full_demo.db
```

(Use forward slashes on Windows.)

---

## Part C — Supabase setup (one-time)

1. Run migrations `001`–`012` in Supabase SQL Editor (including `010`, `011`, `012`).
2. Create **three test users** in Supabase Auth (email/password):

| Email | Role | Department (create in Admin) |
|-------|------|------------------------------|
| `cnps.admin@test.local` | **admin** | — (global) |
| `cnps.manager.douala@test.local` | **manager** | **Direction Douala** |
| `cnps.viewer@test.local` | **viewer** | **Direction Yaoundé** |

3. After first login, assign roles in **Governance → Users** (or SQL on `user_roles`).

4. Create departments: **Direction Douala**, **Direction Yaoundé**, **Direction Garoua** (link to regional offices if column exists).

---

## Part D — Test matrix by role

### IT Administrator (`cnps.admin@test.local`)

| Step | Feature | Expected |
|------|---------|----------|
| 1 | Governance → Overview | Cross-department KPIs, institutional timeline |
| 2 | Governance → Departments | CRUD units, assign users |
| 3 | Governance → Semantic layer | **CNPS Core Schema** fields; map `contribution_amount` → `contributions.contribution_amount`, etc. |
| 4 | Governance → Users | Assign manager/viewer roles + CNPS titles |
| 5 | Governance → Load institutional report | Combined narrative |
| 6 | (Optional) Add analysis preset via API/SQL | New card on Analysis page |

**Semantic mapping cheat sheet (manager DB connection):**

| Global field | Local column | Table |
|--------------|--------------|-------|
| contribution_amount | contribution_amount | contributions |
| contribution_date | contribution_date | contributions |
| employee_id | employee_id | contributions |
| employer_id | employer_id | contributions |
| payment_status | payment_status | contributions |
| pension_amount | pension_amount | pension_payments |
| regional_code | regional_code | contributions |
| accident_date | claim_date | at_mp_claims |
| claim_status | claim_status | at_mp_claims |

---

### Manager — Direction Douala (`cnps.manager.douala@test.local`)

| Step | Page | Action | Validates |
|------|------|--------|-----------|
| 1 | Settings | Save SQLite URI above; Test connection | Connectivity |
| 2 | Settings | Map semantic fields (table above) | Configured ETL |
| 3 | Settings | Analysis focus: *"Focus on Douala regional collection and overdue employers"* | Narrative bias |
| 4 | Settings | **Refresh data** | Full ETL + CNPS validation |
| 5 | Dashboard | KPIs, widgets, narrative, anomalies | Monitoring |
| 6 | **Analysis** | Preset **Contributions Monitoring** | Goal-driven engine |
| 7 | **Analysis** | Custom goal: *"Sum contribution_amount by regional_code for last 6 months"* | Custom NLQ/SQL |
| 8 | **Analysis** | Formula: `total_paid / total_expected` (with context in goal) | Formula mode |
| 9 | Schema Explorer | Refresh schema → see **purple** `contribution`, `payment`, `claim` tags | Classification |
| 10 | Schema Explorer | Run **Contribution trend** ready analysis → chart | Rule analyses |
| 11 | Schema Explorer | **Sync to dashboard** | KPI push |
| 12 | Ask Your Data | *"How many overdue contributions in Bafoussam?"* | NLQ |
| 13 | Custom Report | Executive brief, instruction on Douala overdue employers | Report + analysis run |
| 14 | Reports | History, open saved report | Reporting |
| 15 | Validation | See CNPS checks (staleness, duplicates, regional) | Data quality |
| 16 | AI Analyst | Run full analysis / governance score | Advanced analytics |

---

### Viewer — Direction Yaoundé (`cnps.viewer@test.local`)

| Step | Page | Action | Validates |
|------|------|--------|-----------|
| 1 | Dashboard | View KPIs/narrative (read-only) | RBAC read |
| 2 | Reports | Read history | No Settings/Analysis |
| 3 | Analysis presets list | `GET` presets only if exposed — viewer cannot **run** analysis | Role gate |

Viewer should **not** see Settings, Analysis run, or ETL trigger.

---

## Part E — Feature map (quick reference)

```mermaid
flowchart LR
  subgraph discovery [Schema Explorer]
    Intro[Introspect DB]
    Purple[Purple domain tags]
    Ready[Ready-to-run analyses]
    Intro --> Purple --> Ready
  end
  subgraph config [Admin / Settings]
    Semantic[Semantic template + mappings]
    Presets[(cnps_analysis_presets)]
  end
  subgraph run [Execution]
    ETL[Refresh data / ETL]
    Goal[Analysis goal / preset]
  end
  Intro --> Ready
  Semantic --> ETL
  Presets --> Goal
  Ready --> KPIs[(kpi_results)]
  ETL --> KPIs
  Goal --> KPIs
```

---

## Part F — Sample analysis goals to try

| Goal | Type |
|------|------|
| Monthly total contributions by regional office | Preset: Regional Performance |
| Pension disbursement trend last 12 months | Preset: Pension Analytics |
| Count open AT/MP claims by region | Preset: Workplace Accident Analytics |
| Employers with overdue payment_status | Preset: Employer Compliance |
| Compare DOU vs YAO contribution totals | Custom NL goal |

---

## Part G — Troubleshooting

| Issue | Fix |
|-------|-----|
| No purple tags | Table/column names do not match `DOMAIN_KEYWORDS`; rename or extend keywords in `schema_introspector.py` |
| No ready analyses | Table needs both **amount** and **date** column patterns for financial analyses |
| Analysis preset 422 | Run migration `010`; check Supabase `cnps_analysis_presets` |
| ETL empty KPIs | Wrong path in SQLite URI; use absolute path with `sqlite:///` |
| Oracle connection fails | Install Oracle client / use `oracle+oracledb://`; verify service name |

---

## Related docs

- [`CNPS_SAMPLE_DATABASE.md`](CNPS_SAMPLE_DATABASE.md) — smaller sample DB  
- [`CNPS_USER_GUIDE.md`](CNPS_USER_GUIDE.md) — product overview  
- [`SETUP_GUIDE.md`](SETUP_GUIDE.md) — environment setup  
