# Testing Guide

Practical, copy-paste-able recipes to test every feature of the SaaS Analytics
PWA across roles, databases, and connection methods.

---

## 1. Prerequisites

1. Both workflows running (`Backend API` on :8000, `Start application` on :5000).
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

### 2.3 SQLite

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

## 7. Failure-mode checklist

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
