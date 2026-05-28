# SAAS App Class Diagram (Tables + Relationships + Cardinalities + RLS)

This document is derived from:
- `backend/supabase_schema.sql`
- `backend/migrations/*.sql`

> Note: Supabase Auth-managed tables (e.g., `auth.users`) are referenced as FK targets but are not created by your migrations.
>
> Supported external source databases: PostgreSQL, MySQL, Oracle, SQLite, SQL Server, MongoDB.

## 0) Cardinality Legend
- **1 → many**: one target row can be referenced by multiple source rows
- **0..1 → many**: nullable FK / optional association

## 1) Base tables (from `backend/supabase_schema.sql`)

### `database_connections`
- **PK**: `id`
- **FKs**: `user_id` → `auth.users(id)`
- **Columns**: `id, user_id, db_type, host, port, db_name, credentials, connection_method, connection_options, read_only, created_at`
- **Relationships**: `auth.users (1 → many) database_connections`
- **RLS**: policy `user_isolation_db_conn`: `FOR ALL USING (user_id = auth.uid())`

### `notification_recipients`
- **PK**: `id`
- **FKs**: `user_id` → `auth.users(id)`
- **Columns**: `id, user_id, email, preference, opted_out, created_at`
- **Relationships**: `auth.users (1 → many) notification_recipients`
- **RLS**: `user_isolation_notif_rcpt`: `user_id = auth.uid()`

### `kpi_results`
- **PK**: `id`
- **FKs**: `user_id` → `auth.users(id)`
- **Columns**: `id, user_id, kpi_name, value, dod_pct, wow_pct, avg_7d, avg_30d, status, recorded_at, created_at`
- **Governed Mesh additions**: `department_id (FK → departments.id nullable)`, `source_id`, `source_record_count`
- **Relationships**:
  - `auth.users (1 → many) kpi_results`
  - `departments (0..many rows → many kpi_results)` via `kpi_results.department_id`
- **RLS** (governed mesh policies override the original per-user isolation):
  - `kpi_results_admin_all`: admin can `FOR ALL`
  - `kpi_results_dept_select`: `SELECT` if `department_id IN (...) OR user_id = auth.uid()`
  - `kpi_results_dept_insert`: `INSERT` if `department_id IN (...) OR user_id = auth.uid()`

### `anomaly_records`
- **PK**: `id`
- **FKs**: `user_id` → `auth.users(id)`
- **Columns**: `id, user_id, kpi_name, severity, deviation, context, detected_at`
- **Governed Mesh additions**: `department_id (FK → departments.id nullable)`
- **Relationships**:
  - `auth.users (1 → many) anomaly_records`
  - `departments (0..many → many anomaly_records)` via `department_id`
- **RLS**:
  - `anomaly_records_admin_all`: admin `FOR ALL`
  - `anomaly_records_dept_select`: `SELECT` if `department_id IN (...) OR user_id = auth.uid()`
  - `anomaly_records_dept_insert`: `INSERT` gated similarly

### `daily_reports`
- **PK**: `id`
- **FKs**: `user_id` → `auth.users(id)`
- **Columns**: `id, user_id, report_date, narrative, sent_at`
- **Governed Mesh additions**: `department_id (FK → departments.id nullable)`
- **Relationships**:
  - `auth.users (1 → many) daily_reports`
  - `departments (0..many → many daily_reports)` via `department_id`
- **RLS**:
  - `daily_reports_admin_all`: admin `FOR ALL`
  - `daily_reports_dept_select`: `SELECT` if `department_id IN (...) OR user_id = auth.uid()`
  - `daily_reports_dept_insert`: `INSERT` gated similarly

### `user_preferences`
- **PK**: `user_id`
- **FKs**: `user_id` → `auth.users(id)`
- **Columns**: `user_id, ai_tone, sync_time, sync_frequency, yearly_date, analysis_instruction, last_sync_status, created_at, updated_at`
- **Relationships**: `auth.users (1 → 0..1) user_preferences`
- **RLS**: `user_isolation_prefs`: `user_id = auth.uid()`

### `analysis_history`
- **PK**: `id`
- **FKs**: `user_id` → `auth.users(id)`
- **Columns**: `id, user_id, instruction, created_at`
- **Relationships**: `auth.users (1 → many) analysis_history`
- **RLS**: `user_isolation_analysis_hist`: `user_id = auth.uid()`

## 2) Governed Mesh tables (from `backend/migrations/001_governed_mesh.sql`)

### `departments`
- **PK**: `id`
- **FKs**:
  - `template_id` → `semantic_templates(id)` (nullable)
  - `instance_template_id` → `instance_templates(id)` (nullable)
- **Columns**: `id, name, description, instance_url, api_key, template_id, instance_template_id, heartbeat_schedule, heartbeat_time, created_at`
- **Relationships**:
  - `semantic_templates (1 → many departments)` via `template_id`
  - `instance_templates (1 → many departments)` via `instance_template_id`
  - `departments (1 → many user_roles)` via `user_roles.department_id`
- **RLS**:
  - `departments_admin_all`: admin `FOR ALL`
  - `departments_manager_select`: `SELECT` if `id IN (user_roles.department_id for auth.uid())`

### `user_roles`
- **PK**: `id`
- **FKs**:
  - `user_id` → `auth.users(id)` (ON DELETE CASCADE)
  - `department_id` → `departments(id)` (ON DELETE SET NULL)
- **Columns**: `id, user_id, department_id, role, created_at` + `UNIQUE(user_id, department_id)`
- **Relationships**:
  - `auth.users (1 → many user_roles)`
  - `departments (1 → many user_roles)`
- **RLS**:
  - `user_roles_admin_all`: admin `FOR ALL`
  - `user_roles_self_select`: `SELECT` where `user_id = auth.uid()`

### `semantic_templates`
- **PK**: `id`
- **FKs**: `created_by` → `auth.users(id)`
- **Columns**: `id, name, description, created_by, created_at`
- **Relationships**:
  - `semantic_templates (1 → many semantic_fields)`
  - `semantic_templates (0..many departments)` via `departments.template_id`
- **RLS**:
  - read: `semantic_templates_read_all` (`SELECT true`)
  - write: admin-only via `user_roles.role='admin'`

### `semantic_fields`
- **PK**: `id`
- **FKs**: `template_id` → `semantic_templates(id)` (ON DELETE CASCADE)
- **Columns**: `id, template_id, global_field_name, data_type, required, description, created_at`
- **Relationships**:
  - `semantic_templates (1 → many semantic_fields)`
  - `semantic_fields (1 → many field_mappings)` via `field_mappings.template_field_id`
- **RLS**:
  - read: `semantic_fields_read_all` (`SELECT true`)
  - write: admin-only

### `field_mappings`
- **PK**: `id`
- **FKs**:
  - `user_id` → `auth.users(id)`
  - `template_field_id` → `semantic_fields(id)`
- **Columns**: `id, user_id, template_field_id, local_column_name, transformation_rule, created_at, UNIQUE(user_id, template_field_id)`
- **Relationships**:
  - `auth.users (1 → many field_mappings)`
  - `semantic_fields (1 → many field_mappings)`
- **RLS**:
  - `field_mappings_self`: `FOR ALL USING (user_id = auth.uid())`
  - `field_mappings_admin_select`: admin `SELECT`

### `validation_logs`
- **PK**: `id`
- **FKs**:
  - `user_id` → `auth.users(id)`
  - `department_id` → `departments(id)` (nullable)
- **Columns**: `id, user_id, department_id, check_type, status, message, details, created_at`
- **Relationships**:
  - `auth.users (1 → many validation_logs)`
  - `departments (0..many → many validation_logs)` via `department_id`
- **RLS**:
  - `validation_logs_self`: `SELECT` where `user_id = auth.uid()`
  - `validation_logs_admin_all`: admin `FOR ALL`
  - `validation_logs_insert`: `INSERT` gated to `user_id = auth.uid()`

### `instance_templates`
- **PK**: `id`
- **FKs**: `created_by` → `auth.users(id)`
- **Columns**: `id, name, config, created_by, created_at`
- **Relationships**:
  - `instance_templates (1 → many departments)` via `departments.instance_template_id`
- **RLS**:
  - read all
  - admin write only

### `combined_reports`
- **PK**: `id`
- **FKs**: none declared (admin aggregation table)
- **Columns**: `id, report_date, department_breakdown, combined_kpis, narrative, created_at`
- **Relationships**: admin-only table computed from other KPI rows
- **RLS**: `combined_reports_admin`: admin `FOR ALL`

### `source_lineage_records`
- **PK**: `id`
- **FKs**:
  - `user_id` → `auth.users(id)`
  - `department_id` → `departments(id)` nullable
- **Columns**: `id, batch_source_id, user_id, department_id, kpi_name, source_record_id, record_label, record_date, record_value, raw_payload, created_at`
- **Relationships**:
  - `auth.users (1 → many source_lineage_records)`
  - `departments (0..many → many source_lineage_records)` via `department_id`
- **RLS**:
  - admin: `source_lineage_admin_all`
  - department select: `source_lineage_department_select`
  - insert: `source_lineage_insert` where `user_id=auth.uid()`

## 3) Collaboration tables

### `insight_snapshots`
- **PK**: `id`
- **Columns**: `id, user_id, title, content, insight_type, kpi_name, metadata, created_at`
- **Relationships**:
  - `auth.users (1 → many insight_snapshots)` via `user_id`
- **RLS**:
  - `Users manage own snapshots`: `USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)`

## 4) Forecasts + audit tables (from `backend/migrations/003_forecasts_audit.sql`)

### `kpi_forecasts`
- **PK**: `id`
- **FKs**:
  - `department_id` → `departments(id)` (nullable)
- **Columns**: `id, user_id, department_id, kpi_name, forecast_date, predicted_value, lower_bound, upper_bound, generated_at, created_at`
- **Relationships**:
  - `auth.users (1 → many kpi_forecasts)` conceptually via `user_id` + API filtering
  - `departments (0..many → many kpi_forecasts)` via `department_id`
- **RLS**:
  - `Users see own forecasts`: `FOR ALL USING (auth.uid() = user_id)`

### `audit_logs`
- **PK**: `id`
- **Columns**: `id, user_id, action, entity, changes, created_at`
- **Relationships**:
  - `auth.users (1 → many audit_logs)` via `user_id`
- **RLS**:
  - `Users see own audit logs`: `FOR ALL USING (auth.uid() = user_id)`

## 5) Output for diagram tools
You can use this table list directly to build a Mermaid/PlantUML ERD. If you want, tell me which format you prefer (Mermaid ER diagram or PlantUML), and I’ll generate the diagram code from this spec.

