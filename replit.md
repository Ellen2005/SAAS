# SAAS Analytics System

A SaaS analytics platform that connects to a customer's database, auto-discovers
its structure, and runs ready-made business analyses on top of it. Originally
designed with CNPS Cameroon-style use cases (contributions, beneficiaries,
claims, pension forecasting) in mind, but generic enough to support any
relational source.

## Stack

- **Backend**: FastAPI (Python 3.11) on port `8000`
- **Frontend**: React 19 + Vite 6 on port `5000` (proxies `/api/*` → backend)
- **App database**: Supabase (Postgres) – stores users, semantic templates,
  field mappings, KPI results, audit logs, etc.
- **AI**: Groq (Llama 3 70B) for NLQ + auto-mapping suggestions
- **Email**: Brevo for daily/weekly briefings

## Workflows

- `Backend API` – `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --app-dir backend`
- `Start application` – `npm --prefix frontend run dev` (vite, port 5000)

## Auto-Introspection Feature (new)

Built so any customer can connect their database and immediately get:

- **Full schema discovery** – tables, columns, types, primary keys, foreign keys,
  row counts, sample rows. Multilingual classification heuristics (English +
  French) tag tables as `contribution`, `payment`, `beneficiary`, `claim`,
  `pension`, `benefit`, `employer`, `employee`, etc.
- **Suggested analyses** – generated automatically from the discovered tables:
  - Contribution trend over time (monthly time series)
  - Late / missing-payment detection
  - Payment anomaly detection (z-score)
  - Claim throughput
  - Demographic distribution
  - Pension/benefit liability forecast
  - Generic table overviews
- **AI-powered field auto-mapping** – uses Groq to suggest which discovered
  column matches each semantic template field, with a heuristic fallback when
  no API key is configured. Bulk-apply with one click.
- **Generic ETL extraction** – when the legacy hard-coded `source_revenue` /
  `source_inventory` / `source_tickets` queries don't apply, the ETL pipeline
  now uses the introspector to find amount-like + date-like columns on each
  classified table and aggregates daily totals automatically.

### New backend files

- `backend/api/services/schema_introspector.py` – core introspection,
  classification, analysis suggestion and execution logic.
- `backend/api/routers/introspect.py` – endpoints:
  - `POST /api/introspect/schema` – discover schema (cached per user)
  - `POST /api/introspect/auto-map` – LLM-suggested field mappings
  - `POST /api/introspect/apply-mappings` – persist suggestions as field mappings
  - `POST /api/introspect/analyses` – list ready-to-run analyses
  - `POST /api/introspect/run-analysis` – execute a single analysis
  - `DELETE /api/introspect/cache` – invalidate the in-process schema cache
  - `POST /api/introspect/sync-to-kpis` – run every suggested analysis and
    write its summary value into `kpi_results` so it appears on the dashboard
    and in the nightly briefing email. The same logic
    (`run_introspect_sync`) is also called by the APScheduler heartbeat
    after the regular ETL, so discovered analyses keep flowing in nightly
    without any manual click.

### Documentation

- `docs/PROJECT_GUIDE.md` – tech stack, SDLC, 3-month Gantt for re-implementing.
- `docs/TESTING_GUIDE.md` – DB connection-string cookbook (PG/MySQL/SQLite/MSSQL/MongoDB, direct + SSH-tunnel) and role/feature matrix.
- `docs/DEPLOYMENT.md` – push to GitHub, free deploy on Render + Vercel + Supabase.

### New frontend files

- `frontend/src/pages/SchemaExplorer.jsx` – Schema Explorer page (route
  `/explorer`, manager+admin only). Lets the user re-discover the schema,
  browse tables grouped by business domain, view sample rows and FKs, run any
  suggested analysis (chart-rendered), and bulk-apply auto-mapping suggestions.

### Modified files

- `backend/api/main.py` – mounted the new `introspect` router.
- `backend/api/services/etl_service.py` – legacy queries are now best-effort,
  with introspection-driven generic extraction as a fallback before mock data.
- `frontend/src/App.jsx` – lazy-loaded `SchemaExplorer`, added `/explorer`
  route + nav link.
- `frontend/vite.config.js` – binds `0.0.0.0:5000`, allows all hosts, proxies
  `/api/*` to `localhost:8000` so the iframe preview works.
- `frontend/.env` – `VITE_API_URL` cleared so requests use the proxy.

## How a customer uses it

1. Go to **Settings**, configure the database connection (direct, SSH tunnel,
   etc.) and save it.
2. Open **Schema** in the nav. The page calls `POST /api/introspect/schema`
   which connects to the customer DB, walks every schema and table, and
   returns a complete snapshot.
3. Click **Auto-map fields** to let the system propose semantic-template
   mappings; review and apply.
4. Pick any of the suggested analyses (e.g. "Contribution trend over time")
   and click **Run** – the result is rendered as a chart or table.
5. The dashboard's nightly ETL also benefits: when no field mappings exist
   yet, the generic introspection-driven extractor still produces KPIs.

## Notable design choices

- Schema discovery is **cached in-process per user** to avoid re-hammering the
  customer DB on every UI interaction. Re-discover button (or a `DELETE
  /api/introspect/cache` call) invalidates it.
- All discovery/analysis SQL is **read-only** and bounded with `LIMIT`. Row
  counts use `pg_stat_user_tables` on Postgres for fast estimates.
- Auto-mapping prefers the Groq LLM but **degrades gracefully** to keyword
  matching if `GROQ_API_KEY` is missing.
- Multi-dialect SQL: time-series analyses generate Postgres / MySQL / SQLite
  variants from the same spec.
