# Testing Guide

Practical, copy-paste-able recipes to test every feature of the SaaS Analytics
PWA across roles, databases, and connection methods.

---

## 1. Prerequisites

1. Both workflows running (`Backend API` on :8000, `Start application` on :5000).
   - **Windows/local:** from `backend/`, run `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`; from `frontend/`, run `npm run dev` (port 5000, proxies `/api` → :8000).
   - Copy `frontend/.env.example` → `frontend/.env` with your Supabase URL and anon key.
   - In Supabase SQL Editor, run migrations through `006_fix_database_connections.sql` so long Direct URIs save correctly.
2. A Supabase project with the schema applied (`backend/supabase_schema.sql`
   and the migrations under `backend/migrations/`).
3. The following environment variables set in `backend/.env`:

   ```
   SUPABASE_URL=https://<your-project>.supabase.co
   SUPABASE_ANON_KEY=...
   SUPABASE_SERVICE_KEY=...
   DATABASE_URL=postgresql://...           # default fallback DB
   GROQ_API_KEY=...                        # optional, enables NLQ + auto-map
   BREVO_API_KEY=...                       # optional, enables email
   FERNET_KEY=...                          # 32-byte url-safe base64
   ```

4. At least one Supabase auth user. Add yourself a row in `user_roles` with
   `role='admin'` to access admin pages, plus `role='manager'` to test the
   manager surface.

### 1.1 Automated local verification

Run these before pushing or deploying:

```powershell
python -m unittest discover -s tests
python -m compileall backend tests
cd frontend
npm.cmd run lint
npm.cmd run build
```

Expected result:

* Unit/integration tests: `Ran 2 tests ... OK`
* Python compile: no syntax errors
* ESLint: no errors
* Vite build: `built` and PWA service worker files generated

---

## 2. Connection-string cookbook

The **Settings → Connection** page accepts a connection string in the
`credentials` field. Below is the exact format for every supported DB plus
every connection method.

### 2.1 PostgreSQL

| Method | Example you can paste into Settings |
|---|---|
| **Direct (TCP)** | `postgresql://user:password@db.example.com:5432/mydb` |
| **Direct + SSL required** | `postgresql://user:password@db.example.com:5432/mydb?sslmode=require` |
| **Direct + custom schema** | `postgresql://user:password@db.example.com:5432/mydb?options=-c%20search_path%3Dcnps_demo,public` |
| **SSH tunnel** | `postgresql://user:password@127.0.0.1:5432/mydb` plus SSH options below |
| **Supabase pooled** | `postgresql://postgres.<ref>:<password>@aws-0-eu-west-1.pooler.supabase.com:6543/postgres` |

**Public test PostgreSQL you can use right now (read-only):**

```
postgresql://reader:NWDMCE5xdipIjRrp@hh-pgsql-public.ebi.ac.uk:5432/pfmegrnargs
```

This is the EBI / RNAcentral public mirror — perfect for verifying the
schema explorer. Expect ~50 tables.

**SSH-tunnel form (UI fields):**

| Field | Value |
|---|---|
| `db_type` | `postgresql` |
| `host` (where the DB *appears* once tunnelled) | `127.0.0.1` |
| `port` | `5432` |
| `db_name` | `mydb` |
| `credentials` | `postgresql://user:password@127.0.0.1:5432/mydb` |
| `connection_method` | `ssh_tunnel` |
| `connection_options.ssh_host` | `bastion.example.com` |
| `connection_options.ssh_user` | `ubuntu` |
| `connection_options.remote_db_host` | `internal-db.vpc.local` |
| `connection_options.remote_db_port` | `5432` |
| `connection_options.ssh_pkey` | (paste the PEM contents, optional) |

The backend opens a local port, runs `ssh -L`, and rewrites the URL host /
port to `127.0.0.1:<local>` before connecting.

### 2.2 MySQL / MariaDB

| Method | Example |
|---|---|
| **Direct** | `mysql+pymysql://user:password@db.example.com:3306/mydb` |
| **Direct + SSL** | `mysql+pymysql://user:password@db.example.com:3306/mydb?ssl=true` |
| **SSH tunnel** | `mysql+pymysql://user:password@127.0.0.1:3306/mydb` plus the same SSH fields as above |

**Public test MySQL (Rfam, read-only):**

```
mysql+pymysql://rfamro:@mysql-rfam-public.ebi.ac.uk:4497/Rfam
```

(Note: empty password — that is intentional.)

### 2.3 Oracle

Driver used: `oracledb` (installed via `backend/requirements.txt`).

| Method | Example |
|---|---|
| **Direct** | `oracle+oracledb://user:password@db.example.com:1521/service_name` |
| **Direct + service name** | `oracle+oracledb://user:password@db.example.com:1521/ORCL` |
| **SSH tunnel** | `oracle+oracledb://user:password@127.0.0.1:1521/service_name` plus the same SSH fields as above |

For Oracle, use `service_name` or `SID` in the path section of the URI. The current code normalizes `oracle://...` into `oracle+oracledb://...` automatically.

**SSH-tunnel form (UI fields):**

| Field | Value |
|---|---|
| `db_type` | `oracle` |
| `host` (where the DB appears once tunnelled) | `127.0.0.1` |
| `port` | `1521` |
| `db_name` | `service_name` |
| `credentials` | `oracle+oracledb://user:password@127.0.0.1:1521/service_name` |
| `connection_method` | `ssh_tunnel` |
| `connection_options.ssh_host` | `bastion.example.com` |
| `connection_options.ssh_user` | `ubuntu` |
| `connection_options.remote_db_host` | `internal-db.vpc.local` |
| `connection_options.remote_db_port` | `1521` |
| `connection_options.ssh_pkey` | (paste the PEM contents, optional) |

The backend rewrites host/port to the local SSH tunnel endpoint before connecting.

### 2.4 SQLite

SQLite is file-based — there is no host/port/credentials.

| Method | Example |
|---|---|
| **Local file** | `sqlite:///absolute/path/to/database.db` |
| **In-memory (test only)** | `sqlite:///:memory:` |

For SQLite leave `host`, `port`, `db_name` empty in the UI; only set
`credentials` to the URL.

### 2.4 Microsoft SQL Server

Driver used: `pymssql` (already in `requirements.txt`).

| Method | Example |
|---|---|
| **Direct** | `mssql+pymssql://user:password@db.example.com:1433/mydb` |
| **Direct, named instance** | `mssql+pymssql://user:password@db.example.com:1433/mydb?charset=utf8` |
| **Azure SQL** | `mssql+pymssql://user@server:password@server.database.windows.net:1433/mydb` |
| **SSH tunnel** | `mssql+pymssql://user:password@127.0.0.1:1433/mydb` + SSH fields |

### 2.5 MongoDB

Driver used: `pymongo`. Server-side analyses are not yet implemented for
Mongo, but **schema discovery and NLQ work**.

| Method | Example |
|---|---|
| **Atlas SRV** | `mongodb+srv://user:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0` |
| **Direct (single host)** | `mongodb://user:password@db.example.com:27017/mydb?authSource=admin` |
| **Replica set** | `mongodb://user:password@h1:27017,h2:27017,h3:27017/mydb?replicaSet=rs0&authSource=admin` |
| **Local (no auth)** | `mongodb://localhost:27017/mydb` |
| **Atlas with special-char password** | URL-encode the password (e.g. `!` → `%21`, `@` → `%40`) |

> ⚠️ **Atlas gotcha you may hit:** Atlas error `bad auth: Authentication
> failed (code 8000)` is misleading. It can mean **either** wrong username/
> password **or** that the source IP is not on the project's Network Access
> allow-list. To test from Replit / Render / Vercel functions where the
> egress IP changes, add `0.0.0.0/0` to *Network Access* (or a tighter
> CIDR if you know it).

We tested your supplied URI

```
mongodb+srv://ronnytest:12345678!@cluster0.sndc3.mongodb.net/?appName=Cluster0
```

against your cluster from this environment. Both the raw and URL-encoded
forms (`12345678%21`) returned `bad auth`. Likely cause is the IP allow-list
on your Atlas project, or the user / password being slightly different from
what was created. Fix by either:

1. In Atlas → **Network Access** → **Add IP address** → `0.0.0.0/0` (then
   retry), or
2. Re-create the user with a simple ASCII password (no `!`) and try again.

### 2.6 Extra public/sample databases for wider testing

Use these when you want to test more than the two public PostgreSQL/MySQL
servers above.

| Database | Best for | How to use it | Expected result |
|---|---|---|---|
| **EBI Pfam PostgreSQL** (same family as §2.1) | Fast read-only schema + NLQ smoke test | `postgresql://reader:NWDMCE5xdipIjRrp@hh-pgsql-public.ebi.ac.uk:5432/pfmegrnargs` | Test Connection succeeds; Schema Explorer shows dozens of RNA-related tables; NLQ *"List the 5 largest tables by row count"* returns rows. |
| **EBI Rfam MySQL** (same family as §2.2) | MySQL driver + pymysql path | `mysql+pymysql://rfamro:@mysql-rfam-public.ebi.ac.uk:4497/Rfam` | Test Connection succeeds; tables such as `family`, `rfamseq`, `full_region`; suggested analyses run without write access. |
| **Northwind (Azure SQL demo)** | Cloud SQL Server without local install | Microsoft hosts a public demo; connection string format: `mssql+pymssql://demo:password@demo.database.windows.net:1433/Northwind?encrypt=true` — confirm current credentials at https://learn.microsoft.com/en-us/sql/samples/adventureworks-install-configure (Northwind section). | Schema Explorer finds classic `Orders`, `Customers`, `Products`; time-series analyses on order dates. |
| **PostgreSQL Sample Database (Pagila)** | Rich relational schema (DVD rental) | Clone https://github.com/devrimgunduz/pagila and load into local Postgres, or use any hosted copy; URI like `postgresql://postgres:password@localhost:5432/pagila`. | Tables `film`, `customer`, `payment`, `rental`; contribution/payment-style classifications and multiple suggested analyses. |
| **ClickHouse Playground** (optional HTTP/SQL) | Not wired in SAAS today — use only after adding a ClickHouse driver | Public playground docs: https://clickhouse.com/docs/en/getting-started/example-datasets — stick to Postgres/MySQL/SQLite/Mongo until a dialect is added. | N/A until supported. |
| **Chinook** (SQLite/Postgres/MySQL/SQL Server scripts) | Local cross-dialect smoke tests for schema explorer, overview charts, and NLQ | Download from the Chinook GitHub repo: https://github.com/lerocha/chinook-database. For the quickest test, use the SQLite `.sqlite` file and set `credentials` to `sqlite:///C:/absolute/path/Chinook_Sqlite.sqlite`. | Schema Explorer should show music-store tables such as `Album`, `Artist`, `Customer`, `Invoice`, and `InvoiceLine`. Suggested analyses should include invoice/payment-style aggregations. |
| **MongoDB Atlas sample datasets** | Mongo schema discovery, sample documents, and NLQ behavior | Create a free Atlas cluster, click **Load Sample Dataset**, then connect with a URI like `mongodb+srv://user:password@cluster.mongodb.net/sample_analytics?retryWrites=true&w=majority`. MongoDB documents the sample loader here: https://www.mongodb.com/resources/basics/databases/sample-database. | Test Connection should succeed after your IP is allowed. Schema Explorer should show collections such as `accounts`, `customers`, and `transactions` for `sample_analytics`. Server-side SQL analyses are intentionally skipped for Mongo; use NLQ/schema discovery. |
| **AdventureWorks** (SQL Server / Azure SQL) | Enterprise SQL Server governance, lineage, and admin dashboard testing | Download Microsoft sample backups from https://learn.microsoft.com/en-us/sql/samples/adventureworks-install-configure. Restore `AdventureWorksLT` or OLTP into SQL Server/Azure SQL, then use a `mssql+pymssql://...` connection string. | Schema Explorer should discover `SalesLT`/sales tables, many foreign keys, and several amount/date columns. Suggested analyses should produce customer/order totals and time-series rows. |
| **Wide World Importers** (SQL Server / Azure SQL) | Larger operational analytics and admin combined reports | Use Microsoft's SQL Server samples repo/release documented at https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers. Restore the OLTP or DW database and connect with `mssql+pymssql://...`. | Expect a richer schema with sales, purchasing, warehouse, and application tables. Admin dashboard should be useful for testing larger KPI lists and lineage detail. |

For downloadable samples, the app does not download or host the data itself:
load/restore the database locally or in your managed DB, then paste the
resulting connection string into **Settings -> Connection**.

---

## 3. End-to-end smoke test (manager role)

1. **Login** with a Supabase user that has `user_roles.role = 'manager'`.
2. Navigate to **Settings → Connection** and paste the public Postgres URL
   above. Click **Test Connection** → expect a green success toast.
   Click **Save**.
3. Go to **Schema Explorer** (`/explorer`).
   * Re-discover should populate ~50 tables, each tagged with a domain pill.
   * Click any table → see columns + 5 sample rows.
   * Pick any "Suggested analysis" with `Run` — chart renders within a few
     seconds.
4. Click **Sync to dashboard**. You should see a card listing every
   produced KPI with NORMAL / WARNING / CRITICAL pills.
5. Open **Dashboard** — KPIs from step 4 are now in the tile grid.
6. Open **Reports History** — at least the seed narrative is shown. Click
   **Resend** to send to your `notification_recipients` (requires
   `BREVO_API_KEY`).
7. Open **Query** (NLQ) → ask "How many tables do I have?" → expect a SQL
   answer.

---

## 4. Auto-discovery test against your own demo schema

If you loaded the bundled CNPS demo schema into your Supabase, set the
connection to your Supabase pooler URL with `?options=-c search_path=cnps_demo`
and run steps 3-5 above. You should see exactly **6 tables** (employers,
beneficiaries, contributions, payments, pensions, claims) and **13
suggested analyses** producing rows like:

```
Contribution trend over time (contributions)        14972.23   NORMAL
Late / missing contribution detection (contributions)  28.00   WARNING
Late / missing contribution detection (payments)       23.00   WARNING
Pension/benefit liability forecast (pensions)        5787.12   NORMAL
…
```

The two `WARNING` rows confirm the date-staleness detector is working.

---

## 5. NLQ test prompts

Try these against the public Postgres mirror:

* "List the 5 largest tables by row count"
* "Show columns of the rnc_database table"
* "How many distinct organisms are there?"

Against the CNPS demo schema:

* "Show total contributions by month for the last 12 months"
* "Which employers have the most beneficiaries?"
* "Average payment amount in 2025 by region"

---

## 6. Role-based functional matrix

| Page / endpoint | viewer | manager | admin |
|---|---|---|---|
| `/login` | ✅ | ✅ | ✅ |
| `/dashboard` (read KPIs) | ✅ | ✅ | ✅ |
| `/reports` (history) | ✅ | ✅ | ✅ |
| `/reports/custom` (create) | ❌ 403 | ✅ | ✅ |
| `/explorer` Re-discover / Auto-map / Run / Sync | ❌ 403 | ✅ | ✅ |
| `/settings` (save connection / prefs) | ❌ 403 | ✅ | ✅ |
| `/admin/*` (departments, semantic, templates, users, validation) | ❌ 403 | ❌ 403 | ✅ |
| `POST /api/etl/trigger` | ❌ 403 | ✅ | ✅ |
| `POST /api/nlq` | ❌ 403 | ✅ | ✅ |
| `GET /api/audit-log` | ❌ 403 | ✅ (own) | ✅ (own) |

Test each row by signing in as a user assigned that role in `user_roles`.

---

## 7. Email — sending a test message

A dedicated admin endpoint is available so you do not have to wait for the
nightly briefing cron to verify Brevo:

```bash
curl -X POST https://YOUR-API/api/admin/test-email \
     -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d '{ "email": "you@example.com" }'
```

Or trigger it from the in-app **Settings** page (Send Test Email button).

If the response is `502 Brevo error: Key not found / unauthorized`, your
`BREVO_API_KEY` is the legacy `xsmtpsib-…` format that Brevo deprecated in
2024. Generate a new key (it should start with `xkeysib-`) at
https://app.brevo.com/settings/keys/api and put it in your `.env`. The from
address (`EMAIL_SENDER_ADDRESS`) must be a verified sender at
https://app.brevo.com/senders/list.

## 8. Downloading a report

Open `/reports`, click **Download** on any row. The browser receives a
self-contained HTML file (`report-2026-04-30.html`) that opens the print
dialog automatically — choose *Save as PDF* or send it to a real printer.

This works on every browser without requiring server-side PDF libraries
(weasyprint / wkhtmltopdf / chromium), which keeps the free-tier deploy
slim.

## 9. Failure-mode checklist

For each of the following, confirm the UI shows a friendly error rather
than a stack trace or silent failure:

* Wrong DB credentials → red banner with the driver's error string
* Network unreachable → 502 with the timeout message
* Atlas IP not whitelisted → "bad auth" surfaced as warning
* Empty schema (no tables) → Schema Explorer shows "No tables discovered"
* Sync runs but a single analysis fails → KPI card lists per-analysis errors
* Brevo quota exhausted → email service logs a warning, ETL still completes
* Groq missing key → NLQ returns 400 with "AI key not configured"

---

## 8. Re-running the introspect sync from a script

```python
from api.routers.introspect import run_introspect_sync
from api.core.supabase_client import get_supabase

supabase = get_supabase()
print(run_introspect_sync("<user-uuid>", supabase, refresh=True))
```

Useful when you have just loaded fresh data and want to populate the
dashboard before the next nightly heartbeat.
