# Project Guide — SaaS Analytics PWA

End-to-end guide for someone re-implementing this project from scratch over a
**3-month** timeline. Covers the architecture, tech stack, an SDLC plan, and a
Gantt-style schedule of milestones.

---

## 1. What you are building

A multi-tenant SaaS analytics PWA that:

1. Lets a customer connect their own database (PostgreSQL, MySQL, SQLite, SQL
   Server, MongoDB) — directly or through an SSH tunnel.
2. Auto-introspects that database, classifies its tables into business
   domains (contributions, payments, beneficiaries, claims, pensions,
   employers, employees…), and maps columns to a reusable semantic template.
3. Runs ready-made analyses (trend, late-payment detection, anomaly
   z-score, forecasting), pushes the results into a KPI feed, generates an
   AI-written narrative, and emails a daily briefing.
4. Lets users ask plain-English questions of their data ("Natural-Language
   Query") and assemble custom reports.
5. Enforces row-level security so each tenant only sees their own data, with
   admin/manager/viewer roles and a department layer.

---

## 2. Tech stack

### Backend

| Layer | Choice | Why |
|---|---|---|
| Language / runtime | **Python 3.11** | Mature data libraries, fast iteration |
| Web framework | **FastAPI** + **Uvicorn** | Async, type-checked routes, OpenAPI for free |
| ORM / DB driver | **SQLAlchemy 2.x** core + dialect drivers (`psycopg2-binary`, `pymysql`, `pymssql`, `pysqlite3`), **pymongo** | One abstraction, multi-dialect |
| App database & auth | **Supabase** (Postgres + GoTrue) | Hosted, RLS, JWT auth, free tier |
| Scheduling | **APScheduler** (`BackgroundScheduler`) | In-process cron for nightly ETL |
| AI / LLM | **Groq** (Llama-3-70B) via `requests` | Free, fast tokens for narrative + NLQ + auto-mapping |
| Email | **Brevo** REST API | Transactional email free tier |
| Forecasting | **Prophet** | Solid baseline for KPI projections |
| Data plumbing | **pandas**, **numpy** | KPI calc, anomaly scoring |
| Misc | `python-dotenv`, `cryptography` (Fernet for credential encryption), `paramiko` (SSH tunnel) | |

### Frontend

| Layer | Choice |
|---|---|
| Bundler | **Vite 6** |
| Framework | **React 18** |
| Routing | **react-router-dom 6** |
| Charts | **Recharts** |
| Icons | **lucide-react** |
| HTTP | thin `apiJson()` helper with auth header injection |
| PWA | service worker + manifest; English/French i18n |
| Auth | Supabase JS client → JWT in `Authorization: Bearer …` |

### Hosting / DevOps

| Component | Free option |
|---|---|
| Backend | **Render**, **Fly.io**, **Replit Reserved-VM**, or **Railway** (free trial) |
| Frontend | **Vercel** or **Netlify** |
| App DB | **Supabase free tier** (500 MB) |
| Source code | **GitHub** |
| CI | GitHub Actions (lint + test on PR) |
| Secrets | Provider's secret manager (Render env vars, Vercel env, Supabase) |

---

## 3. Repository layout

```
.
├── backend/
│   ├── api/
│   │   ├── core/             # auth, supabase client, scheduler
│   │   ├── routers/          # FastAPI routers (introspect, admin, …)
│   │   ├── services/         # schema_introspector, etl, narrative, …
│   │   └── main.py           # FastAPI app entrypoint
│   ├── migrations/           # Versioned SQL migrations
│   ├── supabase_schema.sql   # Initial schema
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/            # Dashboard, SchemaExplorer, Settings, Admin*…
│   │   ├── components/
│   │   ├── lib/              # api.js, supabaseClient.js, i18n.js
│   │   └── App.jsx
│   ├── index.html
│   └── package.json
├── docs/                     # ← this folder
├── replit.md
└── .replit                   # local dev workflows
```

---

## 4. Data model (Supabase)

Tables (all RLS-protected by `user_id = auth.uid()`):

* `database_connections` — encrypted connection strings + SSH options.
* `notification_recipients` — copy-list for daily briefings.
* `kpi_results` — one row per KPI per day (value, status, dod%, wow%).
* `anomaly_records` — outliers detected by the ETL.
* `daily_reports` — LLM-written narratives.
* `kpi_forecasts` — Prophet projections.
* `user_preferences` — sync time / frequency / AI tone / instructions.
* `analysis_history` — past plain-English instructions.
* `validation_logs` — every connection test, ETL run, KPI write.
* `audit_logs` — sensitive admin actions.
* `source_lineage_records` — explainability ("this KPI came from these rows").

Governed-mesh additions (migration `001`):

* `departments`, `user_roles` (admin/manager/viewer with `department_id`).
* `semantic_templates` + `semantic_fields` — reusable business model.
* `field_mappings` — per-user binding of semantic field → real column.
* `instance_templates`, `combined_reports`.

Forecast / audit additions (migration `003`):

* `kpi_forecasts`, `audit_logs`.

---

## 5. Suggested SDLC

### 5.1 Phases

1. **Discovery (Week 1)** — interview stakeholders, lock the semantic
   template (e.g. CNPS-style: `monthly_contributions`, `late_payments`,
   `claim_throughput`, `pension_liability`), pick the AI provider.
2. **Foundations (Weeks 2-3)** — Supabase project, schema, auth, base
   FastAPI app + React shell with routing & login.
3. **Data ingest (Weeks 4-5)** — connection settings UI, encrypted storage,
   `test-connection` + ETL service writing to `kpi_results`.
4. **Auto-discovery (Weeks 6-7)** — `schema_introspector`, classification
   heuristics, Schema Explorer page, auto-mapping with LLM.
5. **Analytics (Weeks 8-9)** — anomalies, forecasts, NLQ, custom reports,
   narrative generation, briefing email.
6. **Governance (Week 10)** — departments, roles, RLS policies, audit logs,
   validation history.
7. **Hardening (Week 11)** — error handling, retries, rate-limits, PWA,
   i18n, accessibility.
8. **Launch (Week 12)** — load test, security review, deploy backend
   (Render), frontend (Vercel), DNS, monitoring.

### 5.2 Working method

* **Trunk-based** development; one feature branch per ticket.
* Pull requests require a green GitHub Actions run (`pytest -q`, `npm test`,
  `ruff check`, `eslint`).
* **Migrations** are checked in as numbered SQL files; never edit a merged
  one — write a new one.
* **Manual QA** after every backend release using `docs/TESTING_GUIDE.md`.
* Weekly demo + retro on Friday.

---

## 6. Three-month Gantt (12 weeks)

Cell legend: `█` = primary work, `░` = supporting / spillover.

```
Week:                       1  2  3  4  5  6  7  8  9 10 11 12
W1  Discovery & spec       ██  ░
W2  Supabase + auth + base  ░ ██ ██
W3  Frontend shell             ░ ██  ░
W4  Connection settings UI       ░ ██ ██
W5  ETL service (basic)              ░ ██  ░
W6  Schema introspector                 ██ ██
W7  Auto-map + Schema Explorer             ██ ██
W8  Anomalies + forecasts                       ██ ██
W9  NLQ + custom reports + email                   ██ ██
W10 Departments / roles / audit                       ██ ██
W11 Hardening / PWA / i18n                               ██ ██
W12 Deploy + monitoring                                     ██ ██
```

### Milestones

| # | Milestone | Target end of week |
|---|---|---|
| M1 | Login + empty Dashboard live in dev | 3 |
| M2 | Manual ETL writes to `kpi_results` and Dashboard re-renders | 5 |
| M3 | Schema Explorer auto-discovers any DB and runs an analysis | 7 |
| M4 | Daily briefing email sends with anomalies + narrative | 9 |
| M5 | Admin can manage departments, users, templates | 10 |
| M6 | Public deploy with custom domain | 12 |

### Key dependencies

```
M1 → M2 → M3 → M4 → M5 → M6
              ↘                ↗
             auto-mapping   audit logs
```

---

## 7. Risk register

| Risk | Mitigation |
|---|---|
| LLM hallucination on auto-map | Always show suggestions for human approval; never auto-apply |
| Customer DB is private (no public IP) | Ship SSH-tunnel mode, document setup |
| Free-tier email/AI quotas | Add provider failover + per-user rate limit |
| Long-running ETL blocking server | Use FastAPI `BackgroundTasks` + APScheduler |
| Credential leak | Encrypt at rest with Fernet, never log connection strings |
| RLS misconfig | Add a `pytest` that signs in as user A and asserts they cannot read user B's rows |

---

## 8. Definition of Done (per feature)

* [ ] Code merged via PR with at least one approving review
* [ ] Unit test added or extended
* [ ] Manual run-book entry in `docs/TESTING_GUIDE.md`
* [ ] Migration file (if schema touched) committed
* [ ] `replit.md` updated
* [ ] No `print(secret)` / no hard-coded credentials
* [ ] Works for `viewer`, `manager`, and `admin` roles (tested, see role
      matrix in `docs/TESTING_GUIDE.md` §6)

---

## 9. Admin surface

Every admin page in `frontend/src/pages/Admin*.jsx` is gated by
`require_role(["admin"])` on the backend. They are:

| Page | Route | Backend endpoints | Purpose |
|---|---|---|---|
| **Admin Dashboard** | `/admin` | `GET /api/admin/summary`, `GET /api/admin/validation/scorecard`, `GET /api/admin/lineage/{kpi_id}` | Cross-departmental KPI rollup, validation scorecard, drill-down to source rows |
| **Departments** | `/admin/departments` | `GET/POST/DELETE /api/departments`, `POST /api/departments/{id}/assign-user` | CRUD departments and assign users |
| **Semantic Templates** | `/admin/semantic` | `GET/POST/DELETE /api/admin/semantic/templates(/fields)` | Define which business concepts your KPIs measure |
| **Instance Templates** | `/admin/templates` | `GET/POST/DELETE /api/templates/instances`, `POST /api/templates/deploy` | Per-customer customised template snapshots |
| **Users & Roles** | `/admin/users` | `GET /api/admin/users`, `POST/DELETE /api/admin/users/{id}/role` | Promote/demote users between admin/manager/viewer |
| **Validation History** | `/admin/validation` | `GET /api/admin/validation/logs` | Inspect every connection test, ETL run and KPI write |
| **Heartbeat status** | (in Admin Dashboard) | `GET /api/admin/heartbeat/status`, `POST /api/admin/heartbeat/trigger/{dept_id}` | See last-sync per department, force a department-wide ETL |

In total **30+ admin endpoints** across 6 routers, all protected. RLS on the
underlying tables means even a SQL injection at the app layer cannot leak
across tenants.

## 10. Reports

Reports are stored in `daily_reports` and surfaced in three ways:

* **In-app history** (`/reports`) — list, expand, edit narrative, resend.
* **Download** — `GET /api/reports/{id}/download` returns a standalone HTML
  file that auto-triggers the browser print dialog. Saves as PDF or prints
  on paper without any server-side PDF dependency. Available to every
  authenticated user (admins, managers, viewers).
* **Email** — Brevo transactional sends to `notification_recipients`.

### Email troubleshooting

* Use `POST /api/admin/test-email` with `{ "email": "you@example.com" }`
  to verify the Brevo wiring without waiting for the nightly cron.
* Brevo deprecated the legacy `xsmtpsib-…` keys in 2024. New keys must
  start with `xkeysib-…`. If your sends fail with `Key not found /
  unauthorized`, rotate the key in your Brevo dashboard
  (https://app.brevo.com/settings/keys/api) and update `BREVO_API_KEY`.
* The "from" address must be a **verified sender** in Brevo
  (https://app.brevo.com/senders/list).

## 11. After launch

* Add multi-tenant billing (Stripe).
* Add Slack / Teams briefing destinations alongside email.
* Replace Groq with self-hosted Llama-3 if costs grow.
* Add `pgvector` semantic search across `analysis_history`.
* Build a public marketplace of `semantic_templates` (one per industry).
