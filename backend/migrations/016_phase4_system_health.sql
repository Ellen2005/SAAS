-- ============================================================================
-- Migration 016: Phase 4 — System Health Monitoring
-- ============================================================================
-- Adds: system_health_checkpoints for periodic health check results
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_health_checkpoints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  overall TEXT NOT NULL,
  checks JSONB NOT NULL DEFAULT '{}',
  checked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_health_checked ON system_health_checkpoints(checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_health_overall ON system_health_checkpoints(overall);

-- Enable RLS
ALTER TABLE system_health_checkpoints ENABLE ROW LEVEL SECURITY;

-- Admin bypass
CREATE POLICY admin_all_health_checkpoints ON system_health_checkpoints
  FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

-- Manager+ can read
CREATE POLICY manager_read_health_checkpoints ON system_health_checkpoints
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM user_roles
      WHERE user_id = auth.uid() AND role IN ('admin', 'manager')
    )
  );
