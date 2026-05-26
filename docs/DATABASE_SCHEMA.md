# Supabase database schema reference

Run migrations in order in the **Supabase SQL Editor**:

| Order | File | Purpose |
|------|------|---------|
| 1 | `backend/supabase_schema.sql` | Core tables + RLS |
| 2 | `backend/migrations/001_governed_mesh.sql` | Departments, roles, semantic layer, validation |
| 3 | `backend/migrations/002_seed_test_data.sql` | Optional legacy demo source tables |
| 4 | `backend/migrations/003_forecasts_audit.sql` | `kpi_forecasts`, `audit_logs` |
| 5 | `backend/migrations/004_insight_snapshots.sql` | `insight_snapshots` (AI Analyst) |
| 6 | `backend/migrations/005_remove_legacy_demo_data.sql` | Remove old demo KPI rows |
| 7 | `backend/migrations/006_fix_database_connections.sql` | TEXT credentials, nullable host |
| 8 | `backend/migrations/007_empty_kpi_template.sql` | Empty admin KPI template |

Then: `SELECT bootstrap_admin('your@email.com');`

## App tables (Supabase `public`)

| Table | Purpose |
|-------|---------|
| `database_connections` | Per-user source DB URI (optional Fernet encryption) |
| `notification_recipients` | Email briefing recipients |
| `kpi_results` | Dashboard KPI cache |
| `anomaly_records` | Z-score anomalies |
| `daily_reports` | AI narrative history |
| `user_preferences` | Sync schedule, tone, analysis focus |
| `analysis_history` | Past analysis-focus text |
| `departments` | Org units |
| `user_roles` | RBAC + department |
| `semantic_templates` | Admin KPI template definitions |
| `semantic_fields` | Admin-defined KPI fields |
| `field_mappings` | Manager column → semantic field |
| `validation_logs` | ETL validation checks |
| `instance_templates` | Per-department config snapshots |
| `combined_reports` | Admin cross-department rollups |
| `source_lineage_records` | KPI → source traceability |
| `kpi_forecasts` | Prophet 7-day projections |
| `audit_logs` | Config change audit |
| `insight_snapshots` | AI Analyst saved insights |

## Auth

- `auth.users` — managed by Supabase Auth (not in migrations above).

## KPI model

- **Admin KPIs** = rows in `semantic_fields` on the department’s `semantic_templates`.
- **No admin fields** → ETL uses **auto-discovery** from the connected database (introspection).
- **No extractable rows** → **database overview** mode (table counts + narrative).

Optional seed tables from `002` (`source_revenue`, etc.) are legacy only; the app does not require them.
