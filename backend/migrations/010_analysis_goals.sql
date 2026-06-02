-- =============================================================================
-- CNPS: Goal-driven analysis + presets
-- Run in Supabase SQL Editor after prior migrations
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.cnps_analysis_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(80) NOT NULL UNIQUE,
    title_en VARCHAR(200) NOT NULL,
    title_fr VARCHAR(200) NOT NULL,
    category VARCHAR(80),
    default_goal_text TEXT NOT NULL,
    required_domains TEXT[] DEFAULT '{}',
    suggested_formula TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.analysis_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    department_id UUID REFERENCES public.departments(id) ON DELETE SET NULL,
    goal_text TEXT NOT NULL,
    goal_type VARCHAR(40) NOT NULL DEFAULT 'natural_language',
    preset_id UUID REFERENCES public.cnps_analysis_presets(id) ON DELETE SET NULL,
    plan_json JSONB,
    status VARCHAR(30) NOT NULL DEFAULT 'planning',
    result_summary TEXT,
    chart_json JSONB,
    metrics_json JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS public.analysis_formulas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    expression TEXT NOT NULL,
    variables_json JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_user_created
    ON public.analysis_runs(user_id, created_at DESC);

ALTER TABLE public.kpi_results
    ADD COLUMN IF NOT EXISTS source VARCHAR(40) DEFAULT 'etl';

-- RLS
ALTER TABLE public.analysis_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_formulas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS analysis_runs_select_own ON public.analysis_runs;
CREATE POLICY analysis_runs_select_own ON public.analysis_runs
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS analysis_runs_insert_own ON public.analysis_runs;
CREATE POLICY analysis_runs_insert_own ON public.analysis_runs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS analysis_runs_update_own ON public.analysis_runs;
CREATE POLICY analysis_runs_update_own ON public.analysis_runs
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS analysis_formulas_all_own ON public.analysis_formulas;
CREATE POLICY analysis_formulas_all_own ON public.analysis_formulas
    FOR ALL USING (auth.uid() = user_id);

-- CNPS analysis presets (idempotent)
INSERT INTO public.cnps_analysis_presets (slug, title_en, title_fr, category, default_goal_text, required_domains, suggested_formula)
VALUES
    (
        'contributions-monitoring',
        'Contributions Monitoring',
        'Suivi des cotisations',
        'Contributions',
        'Monthly contribution collection totals and payment compliance rate by regional office',
        ARRAY['contribution'],
        NULL
    ),
    (
        'pension-analytics',
        'Pension Analytics',
        'Analytique des pensions',
        'Pensions',
        'Monthly pension disbursement trends and beneficiary growth over the last 12 months',
        ARRAY['pension', 'payment'],
        NULL
    ),
    (
        'workplace-accidents',
        'Workplace Accident Analytics',
        'Analytique des sinistres AT/MP',
        'AT/MP',
        'Workplace accident frequency and average claim processing indicators by region',
        ARRAY['claim'],
        NULL
    ),
    (
        'employer-compliance',
        'Employer Compliance',
        'Conformité des employeurs',
        'Compliance',
        'Count of delinquent employers and overdue contribution amounts by region',
        ARRAY['contribution', 'employer'],
        NULL
    ),
    (
        'regional-performance',
        'Regional Performance',
        'Performance régionale',
        'Regional',
        'Regional contribution share and comparative performance across all CNPS offices',
        ARRAY['contribution'],
        NULL
    )
ON CONFLICT (slug) DO UPDATE SET
    title_en = EXCLUDED.title_en,
    title_fr = EXCLUDED.title_fr,
    default_goal_text = EXCLUDED.default_goal_text,
    required_domains = EXCLUDED.required_domains;
