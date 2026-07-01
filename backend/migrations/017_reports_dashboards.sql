-- Migration 017: Create reports and dashboards tables
BEGIN;

-- Reports table
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    title TEXT,
    narrative TEXT,
    report_type TEXT DEFAULT 'daily',
    format TEXT DEFAULT 'html',
    file_path TEXT,
    status TEXT DEFAULT 'generated',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reports_user_created ON reports(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_dept ON reports(department_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);

ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "Users can read own reports"
    ON reports FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users can insert own reports"
    ON reports FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users can update own reports"
    ON reports FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users can delete own reports"
    ON reports FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Admins can read all reports"
    ON reports FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM user_roles
            WHERE user_roles.user_id = auth.uid()
            AND user_roles.role = 'admin'
        )
    );

-- Dashboards table
CREATE TABLE IF NOT EXISTS dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    layout JSONB DEFAULT '[]',
    widgets JSONB DEFAULT '[]',
    is_default BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT FALSE,
    shared_with UUID[] DEFAULT '{}',
    template_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dashboards_user ON dashboards(user_id);
CREATE INDEX IF NOT EXISTS idx_dashboards_public ON dashboards(is_public) WHERE is_public = TRUE;

ALTER TABLE dashboards ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "Users can read own dashboards"
    ON dashboards FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users can read public dashboards"
    ON dashboards FOR SELECT
    TO authenticated
    USING (is_public = TRUE);

CREATE POLICY IF NOT EXISTS "Users can read shared dashboards"
    ON dashboards FOR SELECT
    TO authenticated
    USING (auth.uid() = ANY(shared_with));

CREATE POLICY IF NOT EXISTS "Users can insert own dashboards"
    ON dashboards FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users can update own dashboards"
    ON dashboards FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users can delete own dashboards"
    ON dashboards FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

COMMIT;
