-- Migration 004: insight_snapshots for collaboration feature
-- Run this in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS insight_snapshots (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    insight_type TEXT NOT NULL DEFAULT 'manual',
    kpi_name    TEXT,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insight_snapshots_user_id ON insight_snapshots(user_id);
CREATE INDEX IF NOT EXISTS idx_insight_snapshots_created_at ON insight_snapshots(created_at DESC);

-- Enable RLS
ALTER TABLE insight_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own snapshots"
    ON insight_snapshots FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
