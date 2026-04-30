# SAAS Analytics System — Feature Testing Guide

Complete manual testing checklist for every implemented feature.  
Run both backend (`uvicorn api.main:app --reload`) and frontend (`npm run dev`) before starting.

---

## Prerequisites

| Item | Value |
|---|---|
| Frontend URL | http://localhost:5173 |
| Backend URL | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Admin account | A Supabase user with `role = admin` in `user_roles` |
| Manager account | A Supabase user with `role = manager` in `user_roles` |
| Viewer account | A Supabase user with `role = viewer` in `user_roles` |

---

## 1. Authentication

### 1.1 Sign Up / Sign In
1. Go to http://localhost:5173
2. Click **Get Started** on the landing page → redirects to `/login`
3. Sign up with a new email and password
4. Confirm email via Supabase (check inbox)
5. Sign in — should redirect to `/dashboard`
6. **Expected:** User is auto-provisioned into the `General` department with `manager` role (check `user_roles` table in Supabase)
7. **Expected:** Admin receives an onboarding notification email (if Brevo is configured)

### 1.2 Session Persistence
1. Sign in, then close and reopen the browser tab
2. **Expected:** Still logged in — no redirect to `/login`

### 1.3 Logout
1. Click **Log Out** in the navbar
2. **Expected:** Redirected to `/login`, localStorage cache cleared

### 1.4 Role-Based Navigation
| Role | Should See |
|---|---|
| admin | Admin nav link + all pages |
| manager | Dashboard, Reports, Validation, Settings |
| viewer | Dashboard, Reports only |

---

## 2. Dashboard

### 2.1 Initial Load (No Data)
1. Sign in as a new manager with no prior syncs
2. Go to `/dashboard`
3. **Expected:** "No report yet" empty state with a **Generate First Report** button

### 2.2 Generate Report (ETL Pipeline)
1. Go to Settings → Source Connectivity → enter a valid DB URI or leave blank (mock data will be used)
2. Go to Dashboard → click **Generate Report**
3. **Expected:** Button shows live step labels:
   - `Step 1/6: Deep Extraction...`
   - `Step 2/6: Applying Semantic Mappings...`
   - `Step 3/6: Running Quality Checks...`
   - `Step 4/6: ML Pattern Matching...`
   - `Step 5/6: Storing Results...`
   - `Step 6/6: AI Strategic Writing...`
   - `Finalizing Briefings...`
4. After ~30–60 seconds: KPI cards, AI narrative, and anomaly section appear
5. **Expected:** `last_refreshed` date shown in header

### 2.3 KPI Cards
1. After a successful sync, verify KPI cards show:
   - KPI name (formatted, no underscores)
   - Value with locale formatting
   - DoD % with up/down arrow and color (green = positive, red = negative)
   - Status badge (NORMAL / WARNING / CRITICAL)

### 2.4 AI Narrative
1. **Expected:** Narrative section appears with a structured report (header, executive summary, KPIs, anomalies, priorities)
2. Verify it uses actual numbers from the KPI data, not placeholders

### 2.5 Anomaly Section
1. If any KPI has a z-score > 1.5, the anomaly section appears
2. **Expected:** Each anomaly shows KPI name, reason, and deviation value

### 2.6 Validation Warnings
1. If validation checks fail during sync, a `ValidationWarnings` banner appears at the top of the dashboard
2. **Expected:** Shows check type, status, and message

### 2.7 Dashboard Cache
1. After loading data, disconnect from the internet (or stop the backend)
2. Reload the page
3. **Expected:** Last known data is shown from localStorage cache (no spinner)

### 2.8 Report History Button
1. Click **Report History** button
2. **Expected:** Navigates to `/reports`

---

## 3. Report History

### 3.1 List Reports
1. Go to `/reports`
2. **Expected:** All past reports listed newest-first, each showing date and narrative preview

### 3.2 Expand Report
1. Click a report row
2. **Expected:** Full narrative text expands below

### 3.3 Edit Narrative (Manager/Admin only)
1. Click **Edit** on any report
2. Modify the narrative text
3. Click **Save**
4. **Expected:** Updated text persists; row shows new preview

### 3.4 Resend Report Email (Manager/Admin only)
1. Click **Send** on any report
2. **Expected:** Button shows `Sending…` then `✓ Sent!` for 3 seconds
3. Check email inbox of configured recipients — email should arrive with the report

### 3.5 Refresh Button
1. Click **Refresh**
2. **Expected:** List reloads from the API

---

## 4. Settings

### 4.1 Source Connectivity — Direct Connection
1. Go to `/settings`
2. Select **Direct Connection**
3. Enter a PostgreSQL URI in the **Direct URI** field
4. Click **Test Connection**
5. **Expected:** "Connection verified." message in green
6. Click **Save Connection**
7. **Expected:** "Configuration saved." message

### 4.2 Source Connectivity — SSH Tunnel
1. Select **SSH Tunnel**
2. Fill in SSH Host, SSH User, Remote DB Host
3. Fill in Host, Port, and Direct URI
4. Click **Test Connection**
5. **Expected:** Tunnel is established and connection verified (or error message if SSH is unreachable)

### 4.3 Source Connectivity — Cloudflare Tunnel
1. Select **Cloudflare Tunnel**
2. Enter a tunnel token
3. Save and test
4. **Expected:** Token is saved to `connection_options` in Supabase

### 4.4 Semantic Mapping
1. Go to Settings → Semantic Mapping section
2. **Expected:** Template name shown (or "No semantic template assigned yet")
3. If fields exist: each field shows with a local column input
4. Type a column name (e.g. `total_sales`) and click **Map**
5. **Expected:** Button changes to **Update**, mapping saved to `field_mappings` table
6. If all required fields are mapped: green "Required mappings are complete." message

### 4.5 AI Narrative & Delivery Preferences
1. Change **AI Tone** to `Formal`
2. Change **Sync Frequency** to `Weekly`
3. Set **Sync Time** to `08:00`
4. Add an email in **Email Recipients** (one per line)
5. Click **Save Preferences**
6. **Expected:** "Governed preferences updated." alert
7. Verify in Supabase: `user_preferences` row updated, `notification_recipients` row inserted

### 4.6 Analysis Focus
1. Enter a custom instruction in **Analysis Focus** (e.g. "Focus on revenue quality and margin risk")
2. Save Preferences
3. Run a new sync
4. **Expected:** AI narrative reflects the custom focus

### 4.7 Trigger Sync Now
1. Click **Trigger Sync Now**
2. **Expected:** Alert: "Department sync triggered. Please check the Dashboard for live progress."

### 4.8 Theme Toggle
1. Click **Light** button
2. **Expected:** UI switches to light theme, preference saved in localStorage
3. Click **Dark** to revert

### 4.9 Change Password
1. Enter a new password (min 6 chars) in both fields
2. Click **Update Password**
3. **Expected:** "Password updated successfully." message
4. Sign out and sign back in with the new password

### 4.10 Delete Account
1. Click **Delete My Account**
2. Confirm the dialog
3. **Expected:** Account deleted from Supabase Auth, redirected to `/login`
4. Attempting to sign in with the deleted credentials should fail

---

## 5. Validation History

### 5.1 View Logs
1. Go to `/validation` (manager/admin only)
2. **Expected:** List of validation logs with icon (✓ or ⚠), check type, status, message, and timestamp

### 5.2 Cache Fallback
1. Load the page, then stop the backend
2. Reload
3. **Expected:** Cached logs shown from localStorage

---

## 6. Admin — Overview Dashboard

### 6.1 Load
1. Sign in as admin, go to `/admin`
2. **Expected:** Company Revenue Timeline bar chart, Department Breakdown, Data Quality Scorecard

### 6.2 Revenue Timeline Chart
1. Click a bar in the chart
2. **Expected:** Drill-down section appears showing department breakdown for that period

### 6.3 Department Breakdown
1. Click a department row
2. **Expected:** KPI cards expand showing values and DoD %

### 6.4 KPI Lineage Drill-down
1. Click any KPI card inside a department
2. **Expected:** Modal opens showing source records, department, value, and record count
3. Click outside the modal or **Close**
4. **Expected:** Modal closes

### 6.5 Data Quality Scorecard
1. **Expected:** Each department shows check badges (schema, null, anomaly) with pass/warning/fail colors and an overall % score

---

## 7. Admin — Departments

### 7.1 List Departments
1. Go to `/admin/departments`
2. **Expected:** All departments listed with user count, last sync date, heartbeat schedule

### 7.2 Create Department
1. Click **New Department**
2. Fill in Name, Description, Heartbeat Schedule, Heartbeat Time
3. Click **Create**
4. **Expected:** New department appears in the list

### 7.3 Trigger ETL for Department
1. Click the refresh icon (⟳) on any department
2. **Expected:** Alert: "Triggered ETL for X user(s) in this department."
3. Check Dashboard for sync progress

### 7.4 Delete Department
1. Click the trash icon on a non-critical department
2. Confirm the dialog
3. **Expected:** Department removed; users in that department are unassigned (non-admin roles deleted)

---

## 8. Admin — Users

### 8.1 List Users
1. Go to `/admin/users`
2. **Expected:** Table showing email, role badge, department, and action buttons

### 8.2 Edit User Role
1. Click **Edit** on any user
2. Change role (e.g. viewer → manager) and department
3. Click **Save**
4. **Expected:** Row updates with new role badge and department

### 8.3 Remove User Role
1. Click the trash icon on a user
2. Confirm
3. **Expected:** User removed from `user_roles` table; they will be re-provisioned as manager on next login

---

## 9. Admin — Semantic Layer

### 9.1 Create Template
1. Go to `/admin/semantic`
2. Click **+** next to Templates
3. Enter a name (e.g. "Sales Template") and description
4. Click **Create**
5. **Expected:** Template appears in the left panel

### 9.2 Select Template and Add Field
1. Click the template to select it
2. Click **Add Field**
3. Enter field name (e.g. `net_revenue`), type (`currency`), check **Required**
4. Click **Add**
5. **Expected:** Field appears in the table with REQ badge

### 9.3 Delete Field
1. Click the trash icon next to a field
2. **Expected:** Field removed from the table

### 9.4 Delete Template
1. Click the trash icon on a template
2. Confirm
3. **Expected:** Template and all its fields deleted

---

## 10. Admin — Data Quality

### 10.1 Scorecard
1. Go to `/admin/validation`
2. **Expected:** Grid of department cards with % score and check badges

### 10.2 Audit Log Filter
1. In the Audit Log section, select a filter (e.g. "Null")
2. **Expected:** Table filters to show only null-check logs

### 10.3 Log Detail
1. **Expected:** Each row shows timestamp, department name, check type, status badge, and message

---

## 11. Admin — Instance Templates

### 11.1 Create Template
1. Go to `/admin/templates`
2. Fill in Template Name, Default Frequency, Default Time, AI Tone, Null Threshold
3. Add email recipients (one per line)
4. Optionally add Base Definitions and Base Prompt Template
5. Click **Create Template**
6. **Expected:** Template appears in "Current Templates" section with JSON config

### 11.2 Deploy Template to Department
1. Select a template and a department from the dropdowns
2. Click **Deploy**
3. **Expected:** Alert: "Template deployed to department."
4. Verify in Supabase: `departments.instance_template_id` updated, `user_preferences` updated for all users in that department

---

## 12. Email Notifications

### 12.1 Automated Briefing
1. Add a valid email to Settings → Email Recipients
2. Run a sync (Generate Report)
3. **Expected:** HTML email arrives with:
   - Gradient header with report title and period
   - RAG status badge (🟢/🟡/🔴)
   - AI narrative paragraphs
   - KPI table with DoD/WoW columns
   - Anomaly table
   - "View Full Report" button linking to `/reports`
   - Unsubscribe link in footer

### 12.2 Critical Anomaly Alert
1. Ensure mock data is active (anomalies are injected with z-score > 2.5)
2. Run a sync
3. **Expected:** Separate critical alert email sent for each CRITICAL anomaly with deviation > 3.0σ

### 12.3 Unsubscribe Flow
1. Click the **Unsubscribe** link in any received email
2. **Expected:** Redirected to `/unsubscribe?email=...&token=...`
3. Page confirms unsubscription
4. **Expected:** Email removed from `notification_recipients` table
5. Run another sync — that email should NOT receive the report

---

## 13. Forecasts

### 13.1 Forecast Chart on Dashboard
1. Run a sync (mock data provides 30 days — enough for Prophet)
2. Go to `/dashboard`
3. **Expected:** A **7-Day KPI Forecast** section appears below the KPI cards
4. Chart shows one colored area line per KPI (blue = Net Revenue, green = Inventory Value, amber = Support Tickets)
5. X-axis shows dates in `MM-DD` format; Y-axis abbreviates large values (e.g. `135k`)
6. Hover over the chart — tooltip shows exact predicted value and date
7. Legend at the bottom labels each KPI line

### 13.2 Forecast API
1. Call `GET /api/forecasts` directly
2. **Expected:** 7 rows per KPI with `forecast_date`, `predicted_value`, `lower_bound`, `upper_bound`

> Note: Prophet requires ≥10 historical data points. With mock data (30 days), forecasts are always generated.

---

## 14. Scheduler (Automated Syncs)

### 14.1 Verify Scheduler Starts
1. Start the backend
2. Check logs for: `APScheduler started (1-minute heartbeat for governed mesh syncs).`

### 14.2 Scheduled Sync Trigger
1. Set **Sync Time** in Settings to 1–2 minutes from now
2. Set **Sync Frequency** to `Daily`
3. Wait for the scheduler to fire
4. **Expected:** ETL runs automatically; Dashboard updates with a new report

---

## 15. PWA Features

### 15.1 Offline Banner
1. Load the app, then disconnect from the internet
2. **Expected:** Orange "You are offline" banner appears at the top

### 15.2 Reload Prompt
1. Deploy a new version of the frontend (or update the service worker)
2. **Expected:** "New version available — Reload" prompt appears

### 15.3 Inactivity Warning
1. Leave the app idle for the configured timeout period (default: 10 minutes)
2. **Expected:** Inactivity warning modal appears
3. Click to stay logged in or let it expire

---

## 16. Security & Role Guards

### 16.1 Viewer Cannot Access Settings
1. Sign in as a viewer
2. Navigate to http://localhost:5173/settings
3. **Expected:** Redirected to `/dashboard`

### 16.2 Manager Cannot Access Admin
1. Sign in as a manager
2. Navigate to http://localhost:5173/admin
3. **Expected:** Redirected to `/dashboard`

### 16.3 Unauthenticated Access
1. Sign out
2. Navigate to http://localhost:5173/dashboard
3. **Expected:** Redirected to `/login`

### 16.4 API Role Enforcement
1. As a viewer, call `POST /api/etl/trigger` with a valid bearer token
2. **Expected:** `403 Insufficient permissions`

---

## 17. Audit Log

### 17.1 View Audit Log
1. As a manager or admin, call `GET /api/audit-log`
2. **Expected:** List of config change events (preferences updates, connection saves, report edits)
3. Each entry has `action`, `resource`, `changes`, `created_at`

---

## Known Limitations

| Feature | Status |
|---|---|
| Admin template edit (update existing) | Create and deploy work; in-place editing not wired |
| Viewer-specific read-only dashboard | Viewer sees dashboard but Generate Report is hidden |
| Multi-department user (one user, many depts) | Schema supports it; UI shows first department only |

---

## Quick Smoke Test Sequence (5 minutes)

1. Sign in as manager → Dashboard shows empty state ✓
2. Settings → add email recipient → Save Preferences ✓
3. Dashboard → Generate Report → watch step labels → report appears ✓
4. Reports → expand report → Edit narrative → Save → Send ✓
5. Validation → logs appear ✓
6. Sign out → sign in as admin ✓
7. Admin → Departments → create one → trigger ETL ✓
8. Admin → Users → edit a user role ✓
9. Admin → Semantic → create template → add field ✓
10. Admin → Templates → create instance template → deploy ✓
