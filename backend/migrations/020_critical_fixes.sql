-- Migration 020: Critical Security & Runtime Fixes
-- This migration addresses the most critical issues found in the backend audit.

-- ============================================================
-- 1. Create schema_migrations table (required by migration runner)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 2. Create exec_sql function (required by migration runner)
-- ============================================================
CREATE OR REPLACE FUNCTION public.exec_sql(sql TEXT) RETURNS VOID AS $$
BEGIN
  EXECUTE sql;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- 3. Fix industry column missing in semantic_templates
-- ============================================================
ALTER TABLE public.semantic_templates ADD COLUMN IF NOT EXISTS industry TEXT DEFAULT 'general';

-- ============================================================
-- 4. Add missing FK constraints for orphan record prevention
-- ============================================================
DO $$
BEGIN
  -- kpi_forecasts.user_id
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_kpi_forecasts_user') THEN
    ALTER TABLE public.kpi_forecasts ADD CONSTRAINT fk_kpi_forecasts_user
      FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
  END IF;

  -- audit_logs.user_id
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_audit_logs_user') THEN
    ALTER TABLE public.audit_logs ADD CONSTRAINT fk_audit_logs_user
      FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE SET NULL;
  END IF;

  -- insight_snapshots.user_id
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_insight_snapshots_user') THEN
    ALTER TABLE public.insight_snapshots ADD CONSTRAINT fk_insight_snapshots_user
      FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
  END IF;
END $$;

-- ============================================================
-- 5. Enable RLS on cnps_analysis_presets (was publicly writable)
-- ============================================================
ALTER TABLE public.cnps_analysis_presets ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'admin_all_presets' AND tablename = 'cnps_analysis_presets') THEN
    CREATE POLICY admin_all_presets ON public.cnps_analysis_presets FOR ALL
      USING (EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'auth_read_presets' AND tablename = 'cnps_analysis_presets') THEN
    CREATE POLICY auth_read_presets ON public.cnps_analysis_presets FOR SELECT
      USING (auth.uid() IS NOT NULL);
  END IF;
END $$;

-- ============================================================
-- 6. Enable RLS on kpi_definitions (was publicly writable)
-- ============================================================
ALTER TABLE public.kpi_definitions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'admin_all_kpi_defs' AND tablename = 'kpi_definitions') THEN
    CREATE POLICY admin_all_kpi_defs ON public.kpi_definitions FOR ALL
      USING (EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'auth_read_kpi_defs' AND tablename = 'kpi_definitions') THEN
    CREATE POLICY auth_read_kpi_defs ON public.kpi_definitions FOR SELECT
      USING (auth.uid() IS NOT NULL);
  END IF;
END $$;

-- ============================================================
-- 7. Enable RLS on regional_offices
-- ============================================================
ALTER TABLE public.regional_offices ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'auth_read_regional_offices' AND tablename = 'regional_offices') THEN
    CREATE POLICY auth_read_regional_offices ON public.regional_offices FOR SELECT
      USING (auth.uid() IS NOT NULL);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'admin_all_regional_offices' AND tablename = 'regional_offices') THEN
    CREATE POLICY admin_all_regional_offices ON public.regional_offices FOR ALL
      USING (EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin'));
  END IF;
END $$;

-- ============================================================
-- 8. Add CHECK constraints for data integrity
-- ============================================================
DO $$
BEGIN
  -- user_roles.role
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_role') THEN
    ALTER TABLE public.user_roles ADD CONSTRAINT chk_role CHECK (role IN ('admin', 'manager', 'viewer'));
  END IF;

  -- kpi_results.status
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_kpi_status') THEN
    ALTER TABLE public.kpi_results ADD CONSTRAINT chk_kpi_status CHECK (status IN ('NORMAL', 'WATCH', 'WARNING', 'CRITICAL'));
  END IF;

  -- anomaly_records.severity
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_anomaly_severity') THEN
    ALTER TABLE public.anomaly_records ADD CONSTRAINT chk_anomaly_severity CHECK (severity IN ('WATCH', 'WARNING', 'CRITICAL'));
  END IF;

  -- validation_logs.status
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_validation_status') THEN
    ALTER TABLE public.validation_logs ADD CONSTRAINT chk_validation_status CHECK (status IN ('pass', 'warning', 'fail'));
  END IF;

  -- analysis_runs.status
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_analysis_status') THEN
    ALTER TABLE public.analysis_runs ADD CONSTRAINT chk_analysis_status CHECK (status IN ('planning', 'running', 'completed', 'failed'));
  END IF;

  -- background_jobs.status
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_job_status') THEN
    ALTER TABLE public.background_jobs ADD CONSTRAINT chk_job_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'));
  END IF;
END $$;

-- ============================================================
-- 9. Add missing performance indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_kpi_results_user_recorded ON public.kpi_results(user_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_user_created ON public.analysis_runs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_roles_user_role ON public.user_roles(user_id, role);
CREATE INDEX IF NOT EXISTS idx_kpi_forecasts_dept_date ON public.kpi_forecasts(department_id, forecast_date);

-- ============================================================
-- 10. Add missing updated_at triggers
-- ============================================================
DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOR tbl IN SELECT table_name FROM information_schema.columns
    WHERE column_name = 'updated_at' AND table_schema = 'public'
    AND table_name NOT IN ('user_profiles', 'reports')
  LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_' || tbl) THEN
      EXECUTE format('CREATE TRIGGER set_updated_at_%I BEFORE UPDATE ON public.%I
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()', tbl, tbl);
    END IF;
  END LOOP;
END $$;

-- ============================================================
-- 11. Add partial unique index for default dashboards
-- ============================================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_dashboards_one_default_per_user
  ON public.dashboards(user_id) WHERE is_default = TRUE;

-- ============================================================
-- 12. Add composite unique constraint for daily_reports
-- ============================================================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'daily_reports_user_date_v2_unique') THEN
    ALTER TABLE public.daily_reports ADD CONSTRAINT daily_reports_user_date_v2_unique
      UNIQUE (user_id, report_date);
  END IF;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
