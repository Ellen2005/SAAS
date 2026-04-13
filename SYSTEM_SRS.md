# Software Requirements Specification
## Smart Automated Analytics System (SAAS)
### Decentralized, Department-Owned Progressive Web Application

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) defines the functional and non-functional requirements for the Smart Automated Analytics System (SAAS). It serves as the authoritative reference for design, development, testing, and acceptance of the system. This document reflects the **current implemented system** as of the latest codebase revision.

### 1.2 Scope
SAAS is a Progressive Web Application that enables department managers to connect their own databases, run automated analytics, and receive daily AI-generated briefings via email. The system operates on a **governed mesh architecture**: each department instance is fully isolated at the data level, but a central admin layer aggregates summary reports, manages departments, and oversees data quality across the organization — without accessing raw department data.

Managers access the system through the **PWA dashboard** (installed from a browser or accessed via URL), and also receive results passively through **daily briefing emails**. No BI tool login or query writing is required.

### 1.3 Intended Audience
- Development team (frontend, backend engineers)
- Project managers and scrum masters
- Business stakeholders and department managers
- QA engineers and test leads
- Security and compliance officers

### 1.4 Definitions and Acronyms

| Term / Acronym | Definition |
|---|---|
| SAAS-PWA | Smart Automated Analytics System — Progressive Web App |
| PWA | Progressive Web Application — installable from a browser, no app store needed |
| ETL | Extract, Transform, Load — the data pipeline process |
| KPI | Key Performance Indicator — a measurable metric tracked over time |
| SRS | Software Requirements Specification — this document |
| RBAC | Role-Based Access Control — restricting access based on user roles |
| RLS | Row-Level Security — Supabase database security that isolates user data |
| NLG | Natural Language Generation — producing plain-English text from data |
| LLM | Large Language Model — AI model for generating narrative summaries |
| JWT | JSON Web Token — a signed token used for session authentication |
| CDN | Content Delivery Network — globally distributed servers for fast file delivery |
| BI | Business Intelligence |
| DoD | Day-over-Day — percentage change from the previous day |
| WoW | Week-over-Week — percentage change from the same day last week |
| Governed Mesh | Architecture pattern where departments are autonomous but governed by a shared admin layer |

### 1.5 References
- IEEE Std 830-1998 — Recommended Practice for SRS
- Supabase Documentation — auth, RLS policies, PostgREST
- FastAPI Documentation — Python async web framework
- Brevo (Sendinblue) API Reference — transactional email
- Groq API Reference — cloud LLM inference
- Ollama Documentation — local LLM inference fallback
- Scikit-learn User Guide — anomaly detection
- Workbox Documentation — PWA Service Workers
- APScheduler Documentation — background job scheduling
- Vite PWA Plugin Documentation

---

## 2. Overall System Description

### 2.1 Product Perspective
SAAS is a standalone system, not a module of any existing platform. It is designed on a **governed mesh model**: one isolated department per instance, each connecting only to that department's own data source. A central admin layer provides cross-department observability through aggregated summaries — without accessing raw department data.

The system packages ETL pipeline, ML analytics, AI narrative generation, and a PWA frontend as a self-contained, department-owned tool. Managers access their results in two ways:

1. **PWA Dashboard** — installed from a browser (Chrome, Edge, Safari 16.4+) or accessed via URL. Displays KPI cards, AI narrative, anomaly alerts, validation status, and sync controls.
2. **Daily Briefing Email** — sent automatically at a configured time via Brevo. Contains the AI narrative, KPI status table, anomaly highlights, and a link back to the dashboard. Recipients do not need to log in.

### 2.2 Product Functions (Summary)

| Function Group | Description |
|---|---|
| User Account Management | Sign up / login via Supabase email auth; role assignment (admin / manager / viewer); password reset and account deletion |
| Role-Based Access Control | Three-tier RBAC: admin sees all departments; manager controls their department; viewer has read-only access |
| Database Connectivity | Connect to department's own DB (PostgreSQL, MySQL, SQLite, SQL Server) via direct connection, Cloudflare Tunnel, SSH tunnel, or Docker/VPN |
| Automated ETL | Scheduled pipeline extracts raw data, applies semantic mappings, validates data quality, computes KPIs, detects anomalies, generates AI narrative, and sends email |
| Semantic Layer | Admin-defined global field templates; managers map local DB columns to standardized global field names |
| KPI Computation | Daily computation of DoD %, WoW %, rolling 7-day average; results stored in Supabase for instant dashboard load |
| Anomaly Detection | Z-score deviation analysis flags KPI anomalies as CRITICAL or WARNING after each ETL run |
| AI Narrative Summary | LLM-generated plain-English executive brief per sync; uses Groq API (primary) with Ollama local inference (fallback) and template-based generation (final fallback) |
| Data Validation | Three-check validation gate per ETL run: schema check, null rate check, anomaly magnitude check |
| Dashboard (PWA) | React PWA with KPI cards, AI narrative panel, anomaly feed, validation warnings, sync controls, and offline cache |
| Email Notifications | Daily briefing emails and real-time CRITICAL anomaly alerts via Brevo to configurable recipient list |
| Admin Governance Layer | Cross-department overview: revenue timeline chart, department KPI drill-down, data quality scorecard, user/role management, semantic template management, instance template deployment |
| Offline Capability | Service worker caches last dashboard state; usable without internet |
| Data Lineage | Source records tagged with batch IDs; admin can trace any KPI value back to its source rows |

### 2.3 User Classes and Characteristics

| User Class | Tech Level | Primary Needs | Access Method |
|---|---|---|---|
| Department Manager | Low — non-technical | View daily briefings, trigger syncs, configure DB connection, receive email alerts | PWA dashboard + email |
| System Administrator | High | Manage departments, assign roles, define semantic templates, deploy instance templates, view cross-department analytics | PWA admin panel |
| Viewer | Low | Read-only access to dashboard KPIs and narrative | PWA dashboard |
| Notification Recipient | None required | Receive and read daily briefing emails; no login required | Email only |

### 2.4 Operating Environment
- **Frontend:** Modern browser (Chrome 90+, Edge 90+, Firefox 88+, Safari 16.4+). PWA installable via browser prompt.
- **Backend:** Python 3.10+ runtime. FastAPI + Uvicorn web server. APScheduler for job scheduling.
- **Database:** Supabase (PostgreSQL) for app config, user data, analytics results, validation logs, and lineage records.
- **AI Narrative:** Groq API (primary, cloud LLM — llama3-70b-8192); Ollama local REST API on port 11434 (fallback); template-based generation (final fallback).
- **Email delivery:** Brevo (Sendinblue) transactional email API via `sib-api-v3-sdk`.
- **Source database:** Manager's own PostgreSQL, MySQL, SQLite, or SQL Server instance.
- **Network:** HTTPS required for all production communication. Offline mode served from service worker cache.

### 2.5 Design and Implementation Constraints
- All tools in the stack must have a free tier available.
- No cross-department raw data access is permitted — each department's data is isolated by Supabase RLS and user_id scoping.
- Source databases are accessed in read-only mode; the system must never write to them.
- All analytics (ETL, ML, LLM) run in background tasks, never blocking user sessions.
- The PWA must be installable and function offline using a Workbox service worker.
- Credential storage relies on Supabase's encrypted storage; connection strings are stored per user and never logged.
- The backend exposes a mock mode (`MOCK_DATA=True`) that returns synthetic data when no real DB connection is configured, enabling zero-config onboarding.

---

## 3. Functional Requirements

Requirements are categorized by module. Each has a unique ID (FR-xxx), a priority level (HIGH / MEDIUM / LOW), the requirement statement, and the implementation status reflecting the current codebase.

### 3.1 User Account & Authentication

| ID | Priority | Requirement | Status |
|---|---|---|---|
| FR-001 | HIGH | The system shall allow a user to sign up using an email address and password via Supabase Auth. No credit card or third-party OAuth required. | ✅ Implemented — `Login.jsx` handles `supabase.auth.signUp` |
| FR-002 | HIGH | On successful signup, Supabase shall send an email verification link before granting full access. | ✅ Implemented — handled by Supabase Auth natively |
| FR-003 | MEDIUM | The system shall allow the user to reset their password via an email link sent to their registered address. | ✅ Implemented — `Login.jsx` `handleResetPassword` calls `supabase.auth.resetPasswordForEmail` |
| FR-004 | HIGH | User sessions shall be managed via Supabase JWT tokens. The auth context shall restore sessions on page reload without requiring re-login. | ✅ Implemented — `authContext.jsx` uses `onAuthStateChange` as single source of truth |
| FR-005 | HIGH | The system shall support account deletion. Deleting an account removes the Supabase user and all governed data tied to that account. | ✅ Implemented — `DELETE /api/account` endpoint; `Settings.jsx` `handleDeleteAccount` |
| FR-006 | MEDIUM | The system shall allow authenticated users to change their password from the Settings panel. | ✅ Implemented — `Settings.jsx` calls `supabase.auth.updateUser` |

### 3.2 Role-Based Access Control

| ID | Priority | Requirement | Status |
|---|---|---|---|
| FR-010 | HIGH | The system shall enforce three roles: `admin`, `manager`, and `viewer`. Role assignments are stored in the `user_roles` table and resolved on every authenticated request. | ✅ Implemented — `auth.py` `get_user_info`, `require_role` dependency |
| FR-011 | HIGH | Admin users shall have access to all admin routes and the cross-department governance panel. Manager and viewer roles shall be denied access to admin routes with a 403 response. | ✅ Implemented — `RoleGuard.jsx` on frontend; `require_role(['admin'])` on backend |
| FR-012 | HIGH | Manager users shall have access to the dashboard, validation history, settings, and ETL trigger. Viewer users shall have read-only dashboard access. | ✅ Implemented — `RoleGuard` with `allowedRoles` prop; `require_role(['manager','admin'])` on ETL endpoints |
| FR-013 | MEDIUM | When a new user signs in for the first time with no role assigned, the system shall automatically provision them into the default "General" department with the `manager` role and notify all admin users by email. | ✅ Implemented — `users.py` `get_current_user_info`; `send_admin_onboarding_notification` |
| FR-014 | MEDIUM | Admin users shall be able to assign, change, or remove roles and department assignments for any user via the Admin Users panel. | ✅ Implemented — `AdminUsers.jsx`; `POST /api/admin/users/{id}/role`, `DELETE /api/admin/users/{id}/role` |

### 3.3 Database Connection Management

| ID | Priority | Requirement | Status |
|---|---|---|---|
| FR-020 | HIGH | The system shall support connection to PostgreSQL, MySQL, SQLite, and SQL Server via SQLAlchemy connection strings. | ✅ Implemented — `etl_service.py` `extract_from_source` uses SQLAlchemy |
| FR-021 | HIGH | The system shall support four connection methods: Direct Connection, Cloudflare Tunnel (token-based), SSH Tunnel (key/agent auth), and Docker behind VPN. | ✅ Implemented — `Settings.jsx` connection method selector; `etl_service.py` SSH tunnel logic via `_start_ssh_tunnel` |
| FR-022 | HIGH | A "Test Connection" function shall validate reachability and credentials before saving. | ✅ Implemented — `POST /api/test-connection`; `Settings.jsx` `handleTestConnection` |
| FR-023 | HIGH | Connection details shall be saved per user in the `database_connections` Supabase table. The system shall perform an update-or-insert based on whether a row already exists for the user. | ✅ Implemented — `POST /api/settings/connection` with explicit exists-check logic |
| FR-024 | MEDIUM | SSH tunnel connections shall use local port forwarding with a dynamically allocated free port. The tunnel process shall be terminated after each ETL run. | ✅ Implemented — `_get_free_local_port`, `_start_ssh_tunnel`, `_replace_db_url_host_port` in `etl_service.py` |
| FR-025 | MEDIUM | If no database connection is configured or `MOCK_DATA=True` is set, the system shall fall back to a synthetic 30-day mock dataset to allow zero-config onboarding and testing. | ✅ Implemented — `build_mock_frame()` fallback in `etl_service.py` |

### 3.4 ETL Pipeline

| ID | Priority | Requirement | Status |
|---|---|---|---|
| FR-030 | HIGH | The ETL pipeline shall run automatically on a user-configured schedule (daily, weekly, monthly, or yearly) at a configured time via APScheduler, which checks every minute for due jobs. | ✅ Implemented — `scheduler.py` `process_scheduled_etl` runs on 1-minute interval |
| FR-031 | HIGH | The pipeline shall support department-level heartbeat scheduling in addition to per-user scheduling. Department heartbeats trigger ETL for all users in that department. | ✅ Implemented — `scheduler.py` department heartbeat section; `POST /api/admin/heartbeat/trigger/{dept_id}` |
| FR-032 | HIGH | The pipeline shall execute in six named stages, each updating a `last_sync_status` field in `user_preferences`: FETCHING_DATA → MAPPING_FIELDS → VALIDATING_DATA → ANALYZING_ANOMALIES → LOADING_DATA → GENERATING_AI_NARRATIVE → SENDING_EMAILS → IDLE. | ✅ Implemented — `run_user_etl_pipeline` in `etl_service.py`; `update_sync_status` called at each stage |
| FR-033 | HIGH | The dashboard shall poll `/api/etl/status` every 4 seconds during an active sync and display the current stage label to the user. | ✅ Implemented — `Dashboard.jsx` `handleSync` polling loop with `SYNC_STATUS_LABELS` |
| FR-034 | HIGH | Transformed KPI results, anomaly records, daily reports, and validation logs shall be stored in Supabase after each ETL run. | ✅ Implemented — `run_user_etl_pipeline` inserts to `kpi_results`, `anomaly_records`, `daily_reports`, `validation_logs` |
| FR-035 | MEDIUM | The pipeline shall tag each batch of source records with a `batch_source_id` UUID and store individual source rows in `source_lineage_records` for data lineage tracing. | ✅ Implemented — `store_lineage_records` in `etl_service.py` |
| FR-036 | MEDIUM | A manual "Sync Now" button shall be available on the dashboard (manager role only) and a "Trigger Sync Now" button in Settings to trigger an immediate ETL run. | ✅ Implemented — `POST /api/etl/trigger`; `Dashboard.jsx` and `Settings.jsx` |
| FR-037 | LOW | If validation fails during ETL, the pipeline shall set status to `VALIDATION_FAILED`, still complete the remaining stages, and surface validation warnings on the dashboard. | ✅ Implemented — `run_user_etl_pipeline` continues after `VALIDATION_FAILED`; `ValidationWarnings.jsx` on dashboard |

### 3.5 Semantic Layer

| ID | Priority | Requirement | Status |
|---|---|---|---|
| FR-040 | HIGH | Admin users shall be able to create named semantic templates containing typed global field definitions (field name, data type, required flag, description). | ✅ Implemented — `AdminSemantic.jsx`; `POST /api/admin/semantic/templates` and `/fields` |
| FR-041 | HIGH | Admin users shall be able to assign a semantic template to a department. Managers in that department then map their local DB column names to the global field names. | ✅ Implemented — department `template_id` field; `Settings.jsx` Semantic Mapping section |
| FR-042 | HIGH | The ETL pipeline shall apply field mappings during the MAPPING_FIELDS stage, adding standardized global column names to the DataFrame without removing raw source columns. | ✅ Implemented — `apply_field_mappings` in `etl_service.py` |
| FR-043 | MEDIUM | Field mappings shall support optional transformation rules: multiply by factor, add offset, uppercase, or lowercase. | ✅ Implemented — `apply_field_mappings` transformation rule handling |
| FR-044 | MEDIUM | The system shall validate that all required fields in the assigned template have been mapped before allowing ETL to proceed without a schema validation warning. | ✅ Implemented — `GET /api/semantic/mappings/validate`; `run_schema_check` in `validation_service.py` |

### 3.6 KPI Computation & Anomaly Detection

| ID | Priority | Requirement | Status |
|---|---|---|---|
| FR-050 | HIGH | The system shall compute the following KPI metrics per data point: current value, day-over-day % change (DoD), week-over-week % change (WoW), and rolling 7-day average. | ✅ Implemented — `detect_anomalies_and_transform` in `etl_service.py` |
| FR-051 | HIGH | The system shall use Z-score deviation against the 30-day historical mean and standard deviation to classify KPI status as NORMAL, WARNING (z > 1.5), or CRITICAL (z > 2.5). | ✅ Implemented — `detect_anomalies_and_transform` z-score logic |
| FR-052 | HIGH | Detected anomalies shall include: KPI name, severity, deviation amount, and a plain-English reason string describing the deviation from the 30-day average. | ✅ Implemented — anomaly `context.reason` field in `etl_service.py` |
| FR-053 | MEDIUM | KPI names from source databases shall be normalized to standardized names via a configurable mapping (e.g., "Total Revenue" → "net_revenue"). | ✅ Implemented — `KPI_NAME_MAP` in `etl_service.py` |
| FR-054 | MEDIUM | Admin users shall be able to view per-department KPI values and drill down into individual KPI lineage, showing source records, related KPIs, and batch metadata. | ✅ Implemented — `AdminDashboard.jsx` lineage modal; `GET /api/admin/lineage/{kpi_id}` |

### 3.7 Data Validation

| ID | Priority | Requirement | Status |
|---|---|---|---|
| FR-060 | HIGH | The ETL pipeline shall run three validation checks after the MAPPING_FIELDS stage: schema check (required fields present), null rate check (columns exceeding null threshold), and anomaly magnitude check (month-over-month change exceeding threshold). | ✅ Implemented — `run_all_validations` in `validation_service.py` |
| FR-061 | HIGH | Validation results shall be stored in `validation_logs` with check type, status (pass / warning / fail), message, and details. | ✅ Implemented — `store_validation_results` in `validation_service.py` |
| FR-062 | HIGH | Managers shall be able to view their own validation history on the Validation History page, with offline cache fallback. | ✅ Implemented — `ValidationHistory.jsx`; `GET /api/validation/logs` |
| FR-063 | MEDIUM | Admin users shall be able to view a cross-department data quality scorecard showing per-department scores and check statuses, and a full audit log filterable by check type. | ✅ Implemented — `AdminValidation.jsx`; `GET /api/admin/validation/scorecard` and `/logs` |
| FR-064 | MEDIUM | Null threshold and anomaly magnitude threshold shall be configurable per department via instance templates deployed by the admin. | ✅ Implemented — `get_runtime_config` reads thresholds from `instance_templates.config.validation_rules` |

### 3.8 AI Narrative Summary

| ID | Priority | Requirement | Status |
|---|---|---|---|
| FR-070 | HIGH | The system shall generate a plain-English executive summary after each ETL run describing the most significant KPI movements and anomalies. | ✅ Implemented — `generate_live_narrative` in `narrative_service.py` |
| FR-071 | HIGH | Narrative generation shall use Groq API (llama3-70b-8192) as the primary engine, Ollama local REST API as the first fallback, and a template-based dynamic narrative as the final fallback. | ✅ Implemented — three-tier fallback in `generate_live_narrative` |
| FR-072 | MEDIUM | The AI prompt shall include anchored metric definitions (Net Revenue, DoD %, WoW %, etc.) to ensure consistent terminology across all generated narratives. | ✅ Implemented — `BASE_DEFINITIONS` constant and `build_prompt` in `narrative_service.py` |
| FR-073 | MEDIUM | The AI tone shall be configurable per user as "insight-driven" (punchy, highlight-focused) or "formal" (concise, professional). | ✅ Implemented — `ai_tone` in `user_preferences`; `build_prompt` tone branching |
| FR-074 | MEDIUM | Managers shall be able to provide a custom analysis focus instruction that is injected into the AI prompt as a strategic focus clause. | ✅ Implemented — `analysis_instruction` in `user_preferences`; `CRITICAL STRATEGIC FOCUS` clause in prompt |
| FR-075 | LOW | Custom analysis instructions shall be tracked in an `analysis_history` table. A new entry is only inserted when the instruction changes from the previous run. | ✅ Implemented — `analysis_history` insert logic in `run_user_etl_pipeline` |
| FR-076 | LOW | Instance templates may define a custom base prompt template and base definitions that override the system defaults for all users in a department. | ✅ Implemented — `base_prompt` and `base_definitions` in `get_runtime_config`; passed to `generate_live_narrative` |

### 3.9 PWA Dashboard

| ID | Priority | Requirement | Status |
|---|---|---|---|
| FR-080 | HIGH | The application shall be installable as a PWA from any modern browser via the browser's native install prompt, driven by a `manifest.webmanifest` file. | ✅ Implemented — `vite.config.js` VitePWA plugin; `manifest.webmanifest` in public folder |
| FR-081 | HIGH | The dashboard home screen shall display: KPI status cards with DoD % trend indicators, today's AI narrative, anomaly alerts (if any), validation warnings, and a last-refreshed timestamp. | ✅ Implemented — `Dashboard.jsx` |
| FR-082 | HIGH | The dashboard shall load cached data immediately on open. Fresh data is fetched from the API and the cache is updated on success. On API failure, the last cached result is displayed. | ✅ Implemented — `Dashboard.jsx` localStorage cache with `readDashboardCache` / `writeDashboardCache` |
| FR-083 | HIGH | The PWA shall work offline using a Workbox service worker, serving the most recently cached dashboard state. An offline banner shall be displayed when connectivity is lost. | ✅ Implemented — `vite-plugin-pwa` Workbox config; `OfflineBanner.jsx` |
| FR-084 | MEDIUM | A PWA install/update prompt shall appear when a new service worker version is available or when the browser fires the `beforeinstallprompt` event. | ✅ Implemented — `ReloadPrompt.jsx` using `useRegisterSW` |
| FR-085 | MEDIUM | The admin panel shall provide six sub-sections accessible via a sub-navigation bar: Overview, Departments, Semantic Layer, Data Quality, Users, and Templates. | ✅ Implemented — `AdminSubNav` in `App.jsx`; six admin route/page pairs |
| FR-086 | MEDIUM | The admin overview shall display a company revenue timeline bar chart (drillable by period), department breakdown, and data quality scorecard. | ✅ Implemented — `AdminDashboard.jsx` with Recharts `BarChart` |
| FR-087 | LOW | The dashboard shall support light and dark themes, toggled from the Settings panel. The selected theme shall persist in localStorage. | ✅ Implemented — `Settings.jsx` theme toggle; `index.css` `.light-theme` CSS class |

### 3.10 Notification & Email System

| ID | Priority | Requirement | Status |
|---|---|---|---|
| FR-090 | HIGH | The system shall send a daily briefing email to all configured recipients after each ETL run completes, containing: AI narrative, KPI status cards with trend colors, anomaly digest, and a KPI trend chart image. | ✅ Implemented — `send_automated_briefing` in `email_service.py`; HTML email via Brevo |
| FR-091 | HIGH | When a CRITICAL anomaly is detected (z-score > 3.0), the system shall send a separate immediate alert email to all recipients in addition to the daily digest. | ✅ Implemented — `critical_anomalies` filter and individual alert loop in `send_automated_briefing` |
| FR-092 | HIGH | If the Brevo API key is not configured, the email system shall operate in simulation mode, logging what would have been sent without raising an error. | ✅ Implemented — `get_brevo_client()` returns None; mock path in `send_automated_briefing` |
| FR-093 | MEDIUM | Managers shall be able to add email recipients via the Settings panel. Recipients are stored in the `notification_recipients` table per user. | ✅ Implemented — `Settings.jsx` recipients textarea; `supabase.from('notification_recipients')` upsert |
| FR-094 | MEDIUM | When a new user is first provisioned into the system, all admin users shall receive an onboarding notification email. | ✅ Implemented — `send_admin_onboarding_notification` in `email_service.py` |

### 3.11 Settings & Configuration

| ID | Priority | Requirement | Status |
|---|---|---|---|
| FR-100 | HIGH | The settings panel shall allow the manager to configure: database connection (with connection method), AI tone, sync frequency, sync time, yearly date, analysis focus instruction, and email recipients. | ✅ Implemented — `Settings.jsx` full settings page |
| FR-101 | HIGH | All settings shall be loaded in parallel on page open using `Promise.all` across Supabase and API calls to minimize load time. | ✅ Implemented — `Settings.jsx` `loadSettings` uses `Promise.all` for five concurrent requests |
| FR-102 | MEDIUM | The settings panel shall display the current semantic mapping status, showing which required fields are mapped and which are missing. | ✅ Implemented — `Settings.jsx` Semantic Mapping section with `mappingStatus` validation |
| FR-103 | MEDIUM | Admin users shall be able to create and deploy instance templates that pre-configure sync schedule, AI tone, validation thresholds, email recipients, base definitions, and base prompt for an entire department. | ✅ Implemented — `AdminTemplates.jsx`; `POST /api/templates/instances`; `POST /api/templates/deploy` |


---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Priority | Requirement | Status |
|---|---|---|---|
| NFR-001 | HIGH | Dashboard home screen shall load cached KPI data and narrative immediately on open (sub-100ms from localStorage), with fresh API data replacing it within 2 seconds on a standard connection. | ✅ Implemented — localStorage cache-first strategy in `Dashboard.jsx` |
| NFR-002 | HIGH | All settings data (connection, preferences, semantic mappings, validation status) shall be loaded in a single parallel batch on Settings page open. | ✅ Implemented — `Promise.all` with five concurrent requests in `Settings.jsx` |
| NFR-003 | HIGH | The admin departments list shall load using batched queries (user counts, last sync dates, template names) rather than per-department sequential queries, eliminating N+1 database round-trips. | ✅ Implemented — `departments.py` batch query refactor using `.in_()` filters |
| NFR-004 | HIGH | Each protected API endpoint shall resolve the acting user's role and department in a single Supabase query using a relational join, not two separate queries. | ✅ Implemented — `auth.py` `get_user_info` uses `user_roles` join with `departments(name)` |
| NFR-005 | MEDIUM | ETL pipeline stages shall complete within a reasonable time for datasets up to 5 million rows. The sync status is polled every 4 seconds by the frontend to provide live progress feedback. | ✅ Implemented — 4-second polling interval in `Dashboard.jsx` `handleSync`; 30-attempt timeout |
| NFR-006 | MEDIUM | Email delivery shall occur within the ETL run completion window. Brevo API calls are made synchronously within the background ETL task, not as a separate scheduled job. | ✅ Implemented — `send_automated_briefing` called inside `run_user_etl_pipeline` |

### 4.2 Security

| ID | Priority | Requirement | Status |
|---|---|---|---|
| NFR-010 | HIGH | All API endpoints shall require a valid Supabase JWT in the `Authorization: Bearer` header. Unauthenticated requests shall return 401. | ✅ Implemented — `resolve_user_id` and `get_current_user` in `auth.py` |
| NFR-011 | HIGH | The backend shall use the Supabase service role key for admin operations (user listing, role management). The frontend uses only the anon key. | ✅ Implemented — `SUPABASE_SERVICE_KEY` in backend `.env`; `VITE_SUPABASE_ANON_KEY` in frontend `.env` |
| NFR-012 | HIGH | All API endpoints shall enforce RBAC. Role violations shall return 403 with a message stating the required and actual role. | ✅ Implemented — `require_role` dependency raises `HTTPException(403)` |
| NFR-013 | HIGH | On logout or session expiry, all locally cached sensitive data (dashboard summary, validation logs) shall be cleared from localStorage. | ✅ Implemented — `resetAuthState` in `authContext.jsx`; `handleLogout` in `App.jsx` |
| NFR-014 | HIGH | The account deletion endpoint shall only accept requests authenticated via a verified JWT bearer token. It shall not accept `X-User-Id` header or query param fallbacks. | ✅ Implemented — `DELETE /api/account` calls `get_current_user(authorization)` directly, not `resolve_user_id` |
| NFR-015 | MEDIUM | CORS shall be restricted to known frontend origins (localhost:5173, localhost:5174, localhost:4173). Production deployment shall update this list to the deployed frontend URL. | ✅ Implemented — `CORSMiddleware` in `main.py` with explicit origin list |
| NFR-016 | MEDIUM | Source database credentials shall never be logged. Connection strings are masked in log output by showing only the host portion after the `@` symbol. | ✅ Implemented — `safe_url = db_url.split("@")[-1]` in `etl_service.py` |

### 4.3 Reliability & Availability

| ID | Priority | Requirement | Status |
|---|---|---|---|
| NFR-020 | HIGH | The ETL pipeline shall handle extraction failures gracefully by falling back to mock data, ensuring the dashboard always has data to display. | ✅ Implemented — `extract_from_source` catches all exceptions and returns `build_mock_frame()` |
| NFR-021 | HIGH | The dashboard shall display the last cached result when the API is unreachable, rather than showing an empty or broken state. | ✅ Implemented — `readDashboardCache` fallback in `Dashboard.jsx` `fetchData` |
| NFR-022 | HIGH | The validation history page shall display the last cached validation logs when the API is unreachable. | ✅ Implemented — `readValidationCache` fallback in `ValidationHistory.jsx` |
| NFR-023 | HIGH | The auth system shall use a single `onAuthStateChange` listener as the source of truth for session state, with a `getSession` safety net to clear loading state if no session event fires. | ✅ Implemented — `authContext.jsx` revised auth flow with `resolvedRef` guard |
| NFR-024 | MEDIUM | The scheduler shall run as a background thread via APScheduler and shall be started on application startup and shut down gracefully on application termination. | ✅ Implemented — `lifespan` context manager in `main.py`; `start_scheduler` / `shutdown_scheduler` |
| NFR-025 | MEDIUM | All admin and ETL background operations shall catch exceptions at the top level and return structured error responses rather than crashing the process. | ✅ Implemented — try/except with structured error returns throughout all routers and `run_user_etl_pipeline` |

### 4.4 Usability

| ID | Priority | Requirement | Status |
|---|---|---|---|
| NFR-030 | HIGH | A non-technical manager shall be able to complete initial setup (install PWA, connect DB, configure preferences) using the in-app Settings panel without external documentation. | ✅ Implemented — Settings page with labeled form groups, connection method selector, and inline status feedback |
| NFR-031 | HIGH | The PWA shall be fully responsive across screen sizes from mobile (360px) to desktop (1920px) using CSS Grid and flexible layouts. | ✅ Implemented — `index.css` responsive grid; `dashboard-grid` auto-fit columns |
| NFR-032 | HIGH | All loading states shall display a spinner with a descriptive label. All error states shall display a human-readable message. Empty states shall explain what action is needed. | ✅ Implemented — loading spinners in all pages; empty state messages throughout |
| NFR-033 | MEDIUM | The sync progress shall be communicated to the user in plain English using named stage labels (e.g., "Step 3/6: Running Quality Checks...") rather than raw status codes. | ✅ Implemented — `SYNC_STATUS_LABELS` map in `Dashboard.jsx` |
| NFR-034 | MEDIUM | The admin panel shall use a persistent sub-navigation bar to allow quick switching between the six admin sections without losing context. | ✅ Implemented — `AdminSubNav` component in `App.jsx` |

### 4.5 Compliance

| ID | Priority | Requirement | Status |
|---|---|---|---|
| NFR-040 | HIGH | User data shall be fully deletable on request via the account deletion flow, which removes the Supabase auth user and all associated governed data. | ✅ Implemented — `DELETE /api/account`; `handleDeleteAccount` in `Settings.jsx` |
| NFR-041 | MEDIUM | The system shall not transmit raw source database records to any third party. Only computed aggregate KPI results and anonymized lineage metadata are stored in Supabase. | ✅ Implemented — ETL stores only computed KPIs, anomalies, narratives, and lineage metadata; raw rows are not forwarded |
| NFR-042 | MEDIUM | Email recipients shall be stored per user and can be removed at any time from the Settings panel. | ✅ Implemented — `notification_recipients` delete + re-insert on preferences save |

---

## 5. External Interface Requirements

### 5.1 User Interfaces
- **PWA frontend:** React 19 + Vite 6, custom CSS with CSS variables for theming, Recharts for interactive charts, Lucide React for icons.
- **Installation:** Standard browser "Add to Home Screen" / "Install App" prompt driven by `manifest.webmanifest` and VitePWA plugin.
- **Email template:** Responsive HTML email generated by `email_service.py`, tested for Brevo delivery. Includes KPI cards, anomaly digest, trend chart image, and narrative.
- **Admin panel:** Six-section sub-navigated admin area accessible only to users with the `admin` role.

### 5.2 Hardware Interfaces
No direct hardware interfaces are required. The system accesses the manager's database over a standard TCP/IP network connection. SSH tunnel and Cloudflare Tunnel modes are available for databases behind firewalls or NAT.

### 5.3 Software Interfaces

| System | Protocol / Library | Purpose |
|---|---|---|
| Supabase | `supabase-py` v2 / Supabase JS v2 | User auth, RLS-enforced data storage, analytics cache, validation logs, lineage records |
| Brevo (Sendinblue) | `sib-api-v3-sdk` REST API | Transactional email for daily briefings and CRITICAL anomaly alerts |
| Groq API | `groq` Python SDK — REST | Primary cloud LLM inference (llama3-70b-8192) for narrative generation |
| Ollama | Local REST API on port 11434 | Local LLM fallback for narrative generation (llama3 model) |
| SQLAlchemy | Python ORM / dialect layer | Read-only extraction from manager's source database |
| APScheduler | `BackgroundScheduler` | 1-minute heartbeat for scheduled ETL job dispatch |
| FastAPI + Uvicorn | ASGI web framework | Backend API server |
| Vite + VitePWA | Build tool + Workbox | Frontend bundling, service worker generation, PWA manifest |
| React Router v7 | Client-side routing | SPA navigation with role-guarded routes |

---

## 6. System Constraints & Limitations

### 6.1 Known Constraints

- **Forecasting not yet implemented:** The original SRS specified 7-day ahead forecasting using Meta Prophet. The current system does not include a forecasting module or forecast screen. Prophet is listed in `requirements.txt` but no forecasting service or route exists. This is a planned future feature.
- **No custom KPI formula builder:** The original SRS specified a custom KPI expression builder (FR-032 in original). The current system uses a fixed `KPI_NAME_MAP` for standardization. Custom formulas are not yet supported.
- **No goal/target tracking:** KPI target values and actual-vs-target visualization are not implemented in the current system.
- **No anomaly day-of-week correction:** The original SRS specified same-day-of-week comparison to avoid weekly seasonality false positives. The current system uses a simple 30-day rolling Z-score without day-of-week adjustment.
- **No email opt-out link:** CAN-SPAM / GDPR-compliant opt-out links are not yet included in outgoing emails.
- **No email delivery tracking:** Bounce tracking and persistent bounce notifications are not implemented.
- **No audit log for configuration changes:** The settings audit log (FR-092 in original) is not implemented.
- **No session inactivity timeout:** The 60-minute inactivity session expiry with extension prompt is not implemented; session management is delegated entirely to Supabase Auth defaults.
- **CORS origins are localhost-only:** Production deployment requires updating the `allow_origins` list in `main.py` to include the deployed frontend URL.
- **Supabase free tier pausing:** Projects are paused after 7 days of inactivity. A keep-alive cron job is recommended for production.
- **Brevo free tier limit:** 300 emails/day. Departments with many recipients or frequent CRITICAL alerts may exhaust this limit.
- **Groq rate limits:** The free tier has request-per-minute limits. High-volume concurrent ETL runs may hit rate limits and fall back to Ollama or template generation.
- **Validation scorecard N+1 query:** `AdminValidation` scorecard endpoint fires one query per department for validation logs. This is a known performance issue for organizations with many departments.

### 6.2 Assumptions
- Each department manager has direct or delegated access to database credentials for their department's data source.
- The source database is accessible over the internet, a VPN, SSH tunnel, or Cloudflare Tunnel that the analytics backend can reach.
- Managers have a working email address and access to a modern browser (Chrome 90+, Edge 90+, or Safari 16.4+).
- The deployment team is comfortable with basic cloud hosting operations (Supabase, a Python ASGI host such as Render or Fly.io, and Vercel or Netlify for the frontend).
- The Groq API key and Brevo API key are configured in the backend `.env` file for production use. Without them, the system operates in simulation mode (mock narratives, no emails sent).

### 6.3 Future Improvements
- **7-day KPI forecasting** using Meta Prophet with confidence bands, displayed on a dedicated Forecasts screen.
- **Custom KPI formula builder** allowing managers to define derived metrics (e.g., Revenue / Orders = Average Order Value).
- **Day-of-week anomaly correction** to reduce false positives from weekly seasonality patterns.
- **Email opt-out links** in all outgoing emails for CAN-SPAM / GDPR Article 21 compliance.
- **Audit log** for all configuration changes (who changed what and when).
- **Session inactivity timeout** with a configurable extension prompt.
- **Aggregator layer** that pulls summary reports from each department instance via the `/api/heartbeat/status` and `/api/ingest` endpoints, analyzes them, and delivers a unified executive dashboard and monthly combined briefing — without breaking department data isolation.
- **MongoDB support** via PyMongo extraction alongside the existing SQLAlchemy dialects.
- **CSV / Excel flat file ingestion** as an alternative to live database connections.

---

## 7. Appendix — Use Case Summaries

### UC-01: Manager Sets Up System for the First Time

| Field | Detail |
|---|---|
| Actor | Department Manager |
| Pre-condition | Manager has a browser-accessible device and database credentials for their department |
| Main Flow | 1. Manager opens PWA URL and installs it from browser via the install prompt. 2. Manager signs up with email and password on the Login page. 3. Verifies email via Supabase verification link. 4. System auto-provisions manager into the "General" department with `manager` role; admin receives onboarding notification email. 5. Manager opens Settings → Source Connectivity, selects connection method, enters credentials, and clicks "Test Connection". 6. On success, clicks "Save Connection". 7. Configures AI tone, sync frequency, sync time, and email recipients in the AI Narrative & Delivery section. 8. Maps local DB columns to semantic template fields in the Semantic Mapping section. 9. Clicks "Trigger Sync Now" to run the first ETL. 10. Dashboard updates with live KPI cards, AI narrative, and validation status. |
| Post-condition | System is active; scheduled ETL will run automatically at the configured time |
| Exceptions | Database connection fails → "Test Connection" shows specific error (host unreachable, bad credentials, etc.) and does not save. ETL fails → dashboard shows last cached data with a "Data refresh pending" indication. |

### UC-02: Manager Reviews Daily Briefing

| Field | Detail |
|---|---|
| Actor | Department Manager (or notification recipient) |
| Pre-condition | Nightly ETL has completed successfully |
| Main Flow | 1. Manager receives briefing email at configured time. 2. Reads AI narrative summary in email. 3. Reviews KPI status cards — notes a WARNING on a metric. 4. Clicks "View Dashboard" link in email. 5. PWA opens (or loads from cache if offline) showing KPI cards with DoD % indicators. 6. Sees validation warnings panel if any checks failed. 7. Decides to investigate — opens Settings to review semantic mappings or triggers a manual re-sync. |
| Post-condition | Manager has taken informed action without logging into any BI tool or running any query |
| Exceptions | ETL failed → email not sent (no recipients warning logged); dashboard shows last cached data. API unreachable → dashboard loads from localStorage cache with offline banner. |

### UC-03: Admin Governs Departments

| Field | Detail |
|---|---|
| Actor | System Administrator |
| Pre-condition | Admin is logged in with `admin` role |
| Main Flow | 1. Admin opens Admin → Overview to see company revenue timeline and department breakdown. 2. Clicks a bar in the timeline chart to drill down into a specific period's department breakdown. 3. Navigates to Admin → Departments to review heartbeat schedules and trigger manual ETL for a specific department. 4. Navigates to Admin → Semantic Layer to create a new field template and assign it to a department. 5. Navigates to Admin → Users to assign a new user to a department with the `manager` role. 6. Navigates to Admin → Templates to create an instance template with default sync schedule, AI tone, and validation thresholds, then deploys it to a department. 7. Navigates to Admin → Data Quality to review the cross-department validation scorecard and audit log. |
| Post-condition | Departments are configured, users are assigned, and governance standards are applied consistently |
| Exceptions | No departments exist → Overview shows empty state with guidance to create departments first. |

### UC-04: Manager Investigates a CRITICAL Anomaly

| Field | Detail |
|---|---|
| Actor | Department Manager |
| Pre-condition | ETL has detected a CRITICAL anomaly (Z-score > 2.5) |
| Main Flow | 1. Manager receives a CRITICAL alert email immediately after ETL completes (separate from the daily digest). 2. Opens PWA dashboard. 3. Sees the anomaly highlighted in the "Critical Anomalies Detected" section with the KPI name, deviation percentage, and plain-English reason. 4. Sees validation warnings panel if related data quality issues were also detected. 5. Contacts relevant team based on the anomaly context. |
| Post-condition | Manager is aware of and has responded to the critical issue within minutes of detection |
| Exceptions | Brevo not configured → alert email not sent; anomaly still visible on dashboard. |

---

*Document version: 2.0 — Reflects current implemented system*
*Last updated: based on codebase as reviewed*
