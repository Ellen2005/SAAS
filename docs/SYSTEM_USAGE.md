# SAAS System Usage & Data Flow

This document explains how the SAAS app works end-to-end, how users should use it, and what you must configure in Supabase / environment variables before it functions.

## 1) High-Level Architecture

- **Authentication** is handled by **Supabase Auth** (email/password and OAuth).
- After login, the frontend calls the backend to resolve the user’s **role** and **department**.
- The backend connects to **Supabase** (service role) to read/write governed data.
- When a user triggers a sync, the backend runs the **ETL pipeline**:
  - fetches source KPI-like data from the user’s configured database
  - applies the user’s **semantic mappings**
  - runs **validation checks**
  - stores KPIs/anomalies/reports back into Supabase
  - generates an AI narrative
  - (optionally) emails a daily briefing via Brevo

```mermaid
flowchart TD
  U[User] -->|Login| S[Supabase Auth]
  S -->|session + access_token| F[Frontend]
  F -->|GET /api/users/me (Bearer JWT)| B[Backend]
  B -->|resolve_user_id + get_user_info| F
  F -->|GET /api/summary| B
  B -->|read kpi_results/anomaly_records/daily_reports/validation_logs| B
  F -->|POST /api/etl/trigger| B
  B -->|run_user_etl_pipeline(user_id)| B
  B -->|extract_from_source -> SQLAlchemy| X[Source DB]
  B -->|field_mappings + semantic_fields| B
  B -->|run_all_validations -> validation_logs| B
  B -->|store kpi_results/anomaly_records/daily_reports| B
  B -->|generate_live_narrative| B
```

## 2) What “Analysis” Means in This System

There is no chat/LLM prompt UI yet. Instead, users “ask for an analysis” by editing **Settings → Analysis Focus**.

When the next sync/ETL runs:
- the backend reads `analysis_instruction` from the user’s preferences
- it passes that instruction into the prompt builder
- the backend generates the dashboard narrative from KPIs + anomalies

How to request analysis:
1. Open **Settings**
2. Edit **Analysis Focus**
3. Click **Trigger Sync Now** (manager path) or wait for your scheduled sync time

## 3) Supabase Setup (Required)

### 3.1 Run the governed-mesh migration

1. Open **Supabase Dashboard**
2. Go to **SQL Editor**
3. Run:
   - `backend/migrations/001_governed_mesh.sql`
4. Then bootstrap the first admin:
   - `SELECT bootstrap_admin('your-admin-email@company.com');`
5. If you already have users created in Supabase Auth, assign them defaults:
   - `SELECT assign_existing_users_to_default();`

### 3.2 Seed ETL test source tables (optional but recommended)

If you want the dashboard to show data without wiring external databases:

- Run `backend/migrations/002_seed_test_data.sql`

This seeds:
- `public.source_revenue`
- `public.source_inventory`
- `public.source_tickets`

### 3.3 Required tables

The app will break if these tables don’t exist (or if you keep `MOCK_DATA=true`):
- `departments`
- `user_roles`
- `semantic_templates`
- `semantic_fields`
- `field_mappings`
- `user_preferences`
- `validation_logs`
- `kpi_results`
- `anomaly_records`
- `daily_reports`

## 4) Environment Variables (Local Setup)

### 4.1 Backend (`backend/.env`)

Create `backend/.env` with:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY` (must be the **service_role** key)
- `GROQ_API_KEY` (optional if using Groq; else provide Ollama separately)
- `BREVO_API_KEY` (optional: enables email sending; if missing, email is simulated)
- `MOCK_DATA=false`

### 4.2 Frontend (`frontend/.env`)

Create `frontend/.env` with:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_URL=http://localhost:8000` (or your backend URL)

### 4.3 Redirect URLs for “Forgot Password”

The forgot password feature uses Supabase Auth email reset links.
Ensure Supabase Auth settings allow redirect back to your login route.

## 5) How Login and Role/Department Resolution Work

1. User signs in using **Supabase Auth**.
2. Frontend calls: `GET /api/users/me` with `Authorization: Bearer <access_token>`.
3. Backend verifies the JWT and resolves the user id.
4. Backend looks up the user’s highest role in `user_roles`.
5. If the user has no role yet, the backend auto-provisions:
   - department: `General`
   - role: `manager`
6. After this first provisioning, the user appears in Admin → Users (because Admin lists `user_roles`).

### Admin notification on first provisioning

On first provisioning into `General` + `manager`, the backend attempts to email all admins (via Brevo) **if** `BREVO_API_KEY` is configured.

## 6) Departments, Users, and Multiple Databases

### 6.1 How users are assigned to departments

Users are assigned to departments through `user_roles`:
- `user_roles.user_id = auth.users.id`
- `user_roles.department_id` points to `departments.id`
- `user_roles.role` is `admin`, `manager`, or `viewer`

Assignment rules in current code:
- On first login, if role is missing, backend assigns `General` + `manager`.
- Admins can change role/department via Admin → Users.

### 6.2 Can multiple users in the same department connect to different databases?

Yes.

Current design is **user-level source connections**, not department-level connections:
- `database_connections` is keyed by `user_id`
- each ETL run fetches from the **logged-in user’s** saved connection string

How it “links” to a department:
- The ETL run stores results with the user’s `department_id`.
- Admin dashboards aggregate by `department_id`.

So you can have:
- User A in `Sales` department with Database A
- User B in `Sales` department with Database B

Admin views will aggregate both users’ KPIs/anomalies for `Sales`.

### 6.3 How are databases from the same department linked?

They are linked logically via:
- `user_roles.department_id`

There is no “single shared database per department” in the current schema. Each user has its own connection.

## 7) Database Connections in Settings

In **Settings → Source Connectivity**, the UI stores:
- `database_connections.db_type`
- `database_connections.credentials` (a full SQLAlchemy connection URI)
- `database_connections.connection_method` and `connection_options` (currently stored; ETL uses primarily the credentials string)

### What values to use

For best results:
1. Prefer filling **Direct URI** with a valid SQLAlchemy connection string.
2. Examples:

**PostgreSQL**
`postgresql+psycopg2://user:password@host:5432/database`

**MySQL**
`mysql+pymysql://user:password@host:3306/database`
Note: your environment must have the required SQLAlchemy driver installed for MySQL.

**Oracle**
`oracle+oracledb://user:password@host:1521/service_name`
Note: requires the Oracle Instant Client or Python `oracledb` driver installation.

**SQLite**
`sqlite:///absolute/path/to/database.sqlite`

**SQL Server**
`mssql+pyodbc://user:password@host:1433/database?driver=ODBC+Driver+17+for+SQL+Server`
Note: requires the ODBC driver and SQLAlchemy pyodbc support.

### Important note about the UI builder

The current UI credential string builder assumes a Postgres-style driver.
If you are using anything other than Postgres, enter the full connection string in **Direct URI**.

## 8) Semantic Templates, Templates in Admin, and Mappings

### 8.1 What “Templates” are for (Admin → Semantic Layer)

Templates define the **global standard schema** that validation expects:
- `semantic_templates`: a named template
- `semantic_fields`: fields (name + type + required flag) inside a template
- `departments.template_id` chooses which template applies to a department

### 8.2 Are mappings created by Admin or users?

Mappings are created by **users** (in **Settings → Semantic Mapping**).

Each mapping maps:
- a template field (`template_field_id`)
- to a local source column name (`local_column_name`)

The backend stores mappings in:
- `field_mappings.user_id`

Then ETL uses those mappings to derive standard columns so validation can run.

## 9) ETL, Validation, and Dashboard Results

Dashboard reads:
- `kpi_results`
- `anomaly_records`
- `daily_reports`
- `validation_logs`

Manager users can run:
- `POST /api/etl/trigger` (background ETL)
- Dashboard polls `GET /api/etl/status`

## 10) PWA Install, Offline Behavior, and What Works Without Internet

### Downloadable / installable PWA

This app uses `vite-plugin-pwa` with a manifest and install prompt support.

To install:
1. Run the app (`npm run dev`)
2. Open the URL in a browser
3. Use the “Install App” prompt/button

### Offline

By default, the PWA caches the **app shell and static assets**.

In addition, the Dashboard and Validation History pages store the latest successful responses in `localStorage`.
If you go offline after visiting:
- Dashboard can show your last cached summary
- Validation History can show your last cached logs

Data is not guaranteed to be “live” offline; it’s last-known cached data.

## 11) Forgot Password and Account Management

### Forgot password

On **Login**, click **Forgot password?**
- It triggers `supabase.auth.resetPasswordForEmail(...)`

### Change password

In **Settings → Account Management**:
- enter a new password
- click **Update Password**

### Delete account

In **Settings → Account Management**:
- click **Delete My Account**
- this calls backend `DELETE /api/account` (service-role delete)
- then the frontend signs you out

## 12) Email Sending: Is it working?

Email sending is implemented using Brevo (Sendinblue) via `backend/api/services/email_service.py`.

What triggers emails today:
- During ETL, `send_automated_briefing(...)` is called.

When it will actually send:
- `BREVO_API_KEY` must exist
- the user must have recipient emails in `notification_recipients`

If `BREVO_API_KEY` is missing:
- the backend runs in simulation mode and does not send real email.

## 13) GitHub: Hiding Environment Variables

Never commit secrets.

This repo’s `.gitignore` is updated to ignore:
- `**/.env`
- `**/.env.local`
- `**/.env.*.local`
- `**/*.env`

Make sure you do not commit:
- `backend/.env`
- `frontend/.env`

## 14) Checklist: What You Might Still Need To Do

1. Run Supabase SQL migration `001_governed_mesh.sql`
2. Bootstrap your first admin with `bootstrap_admin(...)`
3. (Optional) Run `002_seed_test_data.sql` to seed ETL demo source tables
4. Set `backend/.env` keys (especially `SUPABASE_SERVICE_KEY` = service_role)
5. Set `frontend/.env` supabase URL + anon key
6. In app:
   - login with your Supabase Auth email
   - go to **Settings** and connect your source DB via **Direct URI**
   - (manager) click **Trigger Sync Now**

## 15) Current Known Gaps / What Isn’t Implemented Yet

- There is no dedicated “chat” UI; analysis requests are done via **Settings → Analysis Focus**.
- Database tunnel methods (`cloudflare_tunnel`, `ssh_tunnel`, `docker_vpn`) are stored in `database_connections` but are not actively implemented to create live tunnels in the ETL extractor yet.

