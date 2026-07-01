-- ============================================================================
-- Migration 014: Enterprise Foundation Layer
-- ============================================================================
-- Adds tables for: Prompt Management, AI Governance, AI Feedback,
-- AI Metrics, Entity Versioning, and expands audit_logs.
-- ============================================================================

-- ── 1. Expand audit_logs ────────────────────────────────────────────────────
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS ip_address TEXT;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS user_agent TEXT;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS old_value JSONB;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS new_value JSONB;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS duration_ms INTEGER;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS reason TEXT;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS affected_objects JSONB;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS request_id TEXT;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS session_id TEXT;

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action ON audit_logs(user_id, action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_request ON audit_logs(request_id);

-- ── 2. Prompt Templates ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prompt_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  description TEXT,
  template TEXT NOT NULL,
  variables JSONB DEFAULT '[]',
  version INTEGER DEFAULT 1,
  is_active BOOLEAN DEFAULT true,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompt_templates_category ON prompt_templates(category);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_name ON prompt_templates(name);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_active ON prompt_templates(is_active);

-- ── 3. Prompt Versions ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prompt_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_id UUID REFERENCES prompt_templates(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  template TEXT NOT NULL,
  variables JSONB DEFAULT '[]',
  changelog TEXT,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt ON prompt_versions(prompt_id);

-- ── 4. AI Governance Log ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_governance_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id TEXT NOT NULL,
  user_id UUID,
  category TEXT NOT NULL,
  intent TEXT,
  model TEXT NOT NULL,
  model_version TEXT,
  temperature REAL,
  max_tokens INTEGER,
  context_length INTEGER,
  tokens_input INTEGER,
  tokens_output INTEGER,
  tokens_total INTEGER,
  cost_usd REAL,
  latency_ms INTEGER,
  confidence_score REAL,
  safety_status TEXT DEFAULT 'safe',
  prompt_version TEXT,
  response_version TEXT,
  status TEXT NOT NULL,
  error_message TEXT,
  ip_address TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_governance_user ON ai_governance_log(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_governance_category ON ai_governance_log(category);
CREATE INDEX IF NOT EXISTS idx_ai_governance_created ON ai_governance_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_governance_status ON ai_governance_log(status);
CREATE INDEX IF NOT EXISTS idx_ai_governance_request ON ai_governance_log(request_id);

-- ── 5. AI Feedback ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id TEXT NOT NULL,
  user_id UUID,
  rating TEXT NOT NULL,
  comment TEXT,
  category TEXT,
  response_content TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_feedback_rating ON ai_feedback(rating);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_category ON ai_feedback(category);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_created ON ai_feedback(created_at DESC);

-- ── 6. AI Metrics ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  data JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_ai_metrics_type ON ai_metrics(event_type);
CREATE INDEX IF NOT EXISTS idx_ai_metrics_timestamp ON ai_metrics(timestamp DESC);

-- ── 7. Entity Versions ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS entity_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type TEXT NOT NULL,
  entity_id UUID NOT NULL,
  version INTEGER NOT NULL,
  snapshot JSONB NOT NULL,
  changelog TEXT,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entity_versions_entity ON entity_versions(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_versions_version ON entity_versions(entity_type, entity_id, version DESC);

-- ── 8. Grant permissions (Supabase RLS) ─────────────────────────────────────
-- Enable RLS on new tables
ALTER TABLE prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_governance_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_versions ENABLE ROW LEVEL SECURITY;

-- Admin bypass policies
CREATE POLICY admin_all_prompt_templates ON prompt_templates
  FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

CREATE POLICY admin_all_prompt_versions ON prompt_versions
  FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

CREATE POLICY admin_all_ai_governance ON ai_governance_log
  FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

CREATE POLICY admin_all_ai_feedback ON ai_feedback
  FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

CREATE POLICY admin_all_ai_metrics ON ai_metrics
  FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

CREATE POLICY admin_all_entity_versions ON entity_versions
  FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

-- User policies for feedback (users can insert their own)
CREATE POLICY user_insert_feedback ON ai_feedback
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_select_feedback ON ai_feedback
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
    OR auth.uid() = user_id
);

-- Manager+ can read governance and metrics
CREATE POLICY manager_read_governance ON ai_governance_log
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM user_roles
      WHERE user_id = auth.uid() AND role IN ('admin', 'manager')
    )
  );

CREATE POLICY manager_read_metrics ON ai_metrics
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM user_roles
      WHERE user_id = auth.uid() AND role IN ('admin', 'manager')
    )
  );
