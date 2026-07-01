-- ============================================================================
-- Migration 015: Phase 3 — Background Jobs & Feedback Enhancement
-- ============================================================================
-- Adds: background_jobs, job_logs, ai_feedback_summary
-- Enhances: ai_feedback with prompt_name, response_preview, rating as INTEGER
-- ============================================================================

-- ── 1. Background Jobs ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS background_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id TEXT NOT NULL UNIQUE,
  job_type TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  payload JSONB DEFAULT '{}',
  created_by UUID,
  priority INTEGER DEFAULT 0,
  progress_pct INTEGER DEFAULT 0,
  result JSONB,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_background_jobs_status ON background_jobs(status);
CREATE INDEX IF NOT EXISTS idx_background_jobs_type ON background_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_background_jobs_created ON background_jobs(created_at DESC);

-- ── 2. Job Logs ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS job_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id TEXT NOT NULL,
  step TEXT NOT NULL,
  status TEXT NOT NULL,
  detail TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_logs_job ON job_logs(job_id);

-- ── 3. AI Feedback Summary ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_feedback_summary (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category TEXT,
  prompt_name TEXT,
  avg_rating REAL,
  count INTEGER DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(category, prompt_name)
);

CREATE INDEX IF NOT EXISTS idx_ai_feedback_summary_category ON ai_feedback_summary(category);

-- ── 4. Enhance ai_feedback table ──────────────────────────────────────────
-- Add prompt_name, response_preview columns; change rating to INTEGER
ALTER TABLE ai_feedback ADD COLUMN IF NOT EXISTS prompt_name TEXT;
ALTER TABLE ai_feedback ADD COLUMN IF NOT EXISTS response_preview TEXT;

-- Change rating from TEXT to INTEGER if needed
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'ai_feedback' AND column_name = 'rating' AND data_type = 'text'
  ) THEN
    ALTER TABLE ai_feedback ALTER COLUMN rating TYPE INTEGER USING rating::INTEGER;
  END IF;
END $$;

-- Add response_content column if not exists (from migration 014)
ALTER TABLE ai_feedback ADD COLUMN IF NOT EXISTS response_content TEXT;

-- ── 5. Enable RLS ─────────────────────────────────────────────────────────
ALTER TABLE background_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_feedback_summary ENABLE ROW LEVEL SECURITY;

-- Admin bypass policies
CREATE POLICY admin_all_background_jobs ON background_jobs
  FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

CREATE POLICY admin_all_job_logs ON job_logs
  FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

CREATE POLICY admin_all_feedback_summary ON ai_feedback_summary
  FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

-- Manager+ can read jobs
CREATE POLICY manager_read_background_jobs ON background_jobs
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM user_roles
      WHERE user_id = auth.uid() AND role IN ('admin', 'manager')
    )
  );

CREATE POLICY manager_read_job_logs ON job_logs
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM user_roles
      WHERE user_id = auth.uid() AND role IN ('admin', 'manager')
    )
  );
