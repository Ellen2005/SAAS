-- Migration 019: Performance indexes and constraints
-- Adds missing indexes, unique constraints, and performance optimizations
BEGIN;

-- 1. Add unique constraint on daily_reports (user_id, report_date) to prevent duplicates
ALTER TABLE daily_reports
    ADD CONSTRAINT unique_daily_report_user_date UNIQUE (user_id, report_date);

-- 2. Add indexes on high-cardinality query columns
-- kpi_results: main dashboard queries filter by user_id + recorded_at
CREATE INDEX IF NOT EXISTS idx_kpi_results_user_recorded ON kpi_results (user_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_results_dept_recorded ON kpi_results (department_id, recorded_at DESC);

-- anomaly_records: dashboard queries filter by user_id + detected_at
CREATE INDEX IF NOT EXISTS idx_anomaly_records_user_detected ON anomaly_records (user_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_records_dept_detected ON anomaly_records (department_id, detected_at DESC);

-- validation_logs: queries filter by user_id + created_at
CREATE INDEX IF NOT EXISTS idx_validation_logs_user_created ON validation_logs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_logs_dept_created ON validation_logs (department_id, created_at DESC);

-- source_lineage_records: lineage queries by batch_source_id + kpi_name
CREATE INDEX IF NOT EXISTS idx_source_lineage_batch_kpi ON source_lineage_records (batch_source_id, kpi_name);
CREATE INDEX IF NOT EXISTS idx_source_lineage_user_kpi ON source_lineage_records (user_id, kpi_name);

-- 3. Add foreign key cascade for user_roles.department_id
ALTER TABLE user_roles
    DROP CONSTRAINT IF EXISTS user_roles_department_id_fkey,
    ADD CONSTRAINT user_roles_department_id_fkey
        FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL;

-- 4. Fix RLS on kpi_results - allow users to see own records OR records in their department
DROP POLICY IF EXISTS kpi_results_dept_select ON public.kpi_results;
DROP POLICY IF EXISTS kpi_results_dept_insert ON public.kpi_results;

CREATE POLICY kpi_results_dept_select ON public.kpi_results
    FOR SELECT USING (
        user_id = auth.uid()
        OR department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
    );

CREATE POLICY kpi_results_dept_insert ON public.kpi_results
    FOR INSERT WITH CHECK (
        user_id = auth.uid()
        OR department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
    );

-- Same for anomaly_records
DROP POLICY IF EXISTS anomaly_records_dept_select ON public.anomaly_records;
DROP POLICY IF EXISTS anomaly_records_dept_insert ON public.anomaly_records;

CREATE POLICY anomaly_records_dept_select ON public.anomaly_records
    FOR SELECT USING (
        user_id = auth.uid()
        OR department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
    );

CREATE POLICY anomaly_records_dept_insert ON public.anomaly_records
    FOR INSERT WITH CHECK (
        user_id = auth.uid()
        OR department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
    );

-- Same for daily_reports
DROP POLICY IF EXISTS daily_reports_dept_select ON public.daily_reports;
DROP POLICY IF EXISTS daily_reports_dept_insert ON public.daily_reports;

CREATE POLICY daily_reports_dept_select ON public.daily_reports
    FOR SELECT USING (
        user_id = auth.uid()
        OR department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
    );

CREATE POLICY daily_reports_dept_insert ON public.daily_reports
    FOR INSERT WITH CHECK (
        user_id = auth.uid()
        OR department_id IN (SELECT department_id FROM public.user_roles WHERE user_id = auth.uid())
    );

-- 5. Add RLS to combined_reports (was missing)
ALTER TABLE combined_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY combined_reports_admin ON public.combined_reports
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
    );

-- 6. Add index on user_roles for faster role lookups
CREATE INDEX IF NOT EXISTS idx_user_roles_user_dept ON user_roles (user_id, department_id);

-- 7. Add composite index for reports table queries
CREATE INDEX IF NOT EXISTS idx_reports_user_dept_type ON reports (user_id, department_id, report_type);

-- 8. Add index on kpi_forecasts for forecast queries
CREATE INDEX IF NOT EXISTS idx_kpi_forecasts_user_date ON kpi_forecasts (user_id, forecast_date);

-- 9. Add index on analysis_runs for history queries
CREATE INDEX IF NOT EXISTS idx_analysis_runs_user_created ON analysis_runs (user_id, created_at DESC);

COMMIT;