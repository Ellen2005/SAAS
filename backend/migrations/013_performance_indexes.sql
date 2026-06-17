-- ────────────────────────────────────────────────────────────────────────────
-- Migration 013: Performance Indexes
-- Adds critical indexes for query performance at CNPS scale.
-- Run in Supabase SQL Editor.
-- ────────────────────────────────────────────────────────────────────────────

-- 1. kpi_results — Most frequently queried table
CREATE INDEX IF NOT EXISTS idx_kpi_results_user_recorded 
    ON kpi_results (user_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_results_dept_recorded 
    ON kpi_results (department_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_results_kpi_name 
    ON kpi_results (kpi_name);
CREATE INDEX IF NOT EXISTS idx_kpi_results_user_kpi_recorded 
    ON kpi_results (user_id, kpi_name, recorded_at DESC);

-- 2. anomaly_records
CREATE INDEX IF NOT EXISTS idx_anomaly_records_user_detected 
    ON anomaly_records (user_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_records_dept_detected 
    ON anomaly_records (department_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_records_severity 
    ON anomaly_records (severity) WHERE severity IN ('CRITICAL', 'HIGH');

-- 3. daily_reports
CREATE INDEX IF NOT EXISTS idx_daily_reports_user_date 
    ON daily_reports (user_id, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_reports_dept_date 
    ON daily_reports (department_id, report_date DESC);

-- 4. validation_logs
CREATE INDEX IF NOT EXISTS idx_validation_logs_user_created 
    ON validation_logs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_logs_dept_created 
    ON validation_logs (department_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_logs_status 
    ON validation_logs (status) WHERE status = 'fail';

-- 5. analysis_runs
CREATE INDEX IF NOT EXISTS idx_analysis_runs_user_completed 
    ON analysis_runs (user_id, completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_status 
    ON analysis_runs (status);

-- 6. audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_created 
    ON audit_logs (user_id, created_at DESC);

-- 7. user_preferences
CREATE INDEX IF NOT EXISTS idx_user_preferences_sync_time 
    ON user_preferences (sync_time);
CREATE INDEX IF NOT EXISTS idx_user_preferences_sync_status 
    ON user_preferences (last_sync_status) WHERE last_sync_status != 'IDLE';

-- 8. notification_recipients
CREATE INDEX IF NOT EXISTS idx_notification_recipients_email 
    ON notification_recipients (email);

-- 9. field_mappings
CREATE INDEX IF NOT EXISTS idx_field_mappings_user 
    ON field_mappings (user_id);

-- 10. insight_snapshots
CREATE INDEX IF NOT EXISTS idx_insight_snapshots_user_created 
    ON insight_snapshots (user_id, created_at DESC);

-- Vacuum analyze to update query planner
ANALYZE kpi_results;
ANALYZE anomaly_records;
ANALYZE daily_reports;
ANALYZE validation_logs;
ANALYZE analysis_runs;
ANALYZE audit_logs;
ANALYZE user_preferences;
ANALYZE field_mappings;