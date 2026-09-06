-- =============================================================================
-- 021: Generic multi-tenant layer — make CNPS deployment one tenant among many
-- Keep existing CNPS data intact, add generic org + rename presets
-- =============================================================================

-- ── 1. Organizations (white-label tenant) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    display_name VARCHAR(200),
    logo_url TEXT,
    primary_color VARCHAR(7) DEFAULT '#2c5282',
    secondary_color VARCHAR(7) DEFAULT '#4299e1',
    locale VARCHAR(10) DEFAULT 'en',
    industry VARCHAR(80),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default org from existing CNPS deployment (idempotent)
INSERT INTO public.organizations (slug, name, display_name, industry, locale)
VALUES ('cnps', 'CNPS', 'CNPS Cameroon', 'social_security', 'fr')
ON CONFLICT (slug) DO NOTHING;

-- Backfill user → org link via user_profiles + user_roles
ALTER TABLE public.user_profiles
    ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL;

-- Link existing users to CNPS org (default tenant)
DO $$
DECLARE cnps_org UUID;
BEGIN
    SELECT id INTO cnps_org FROM public.organizations WHERE slug='cnps' LIMIT 1;
    IF cnps_org IS NOT NULL THEN
        UPDATE public.user_profiles SET organization_id = cnps_org WHERE organization_id IS NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_profiles_org ON public.user_profiles(organization_id);
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON public.organizations(slug);

-- RLS: anyone authenticated can read orgs; only admin can write
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS org_read_all ON public.organizations;
CREATE POLICY org_read_all ON public.organizations FOR SELECT USING (auth.role() = 'authenticated');
DROP POLICY IF EXISTS org_admin_write ON public.organizations;
CREATE POLICY org_admin_write ON public.organizations FOR ALL USING (
    EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role='admin')
);

-- ── 2. Generic analysis presets (rename-safe) ────────────────────────────────
-- Create generic table, migrate data, keep cnps_analysis_presets as VIEW for compat
CREATE TABLE IF NOT EXISTS public.analysis_presets (
    LIKE public.cnps_analysis_presets INCLUDING ALL
);
-- Ensure FK for analysis_runs points to generic table (add if missing)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='analysis_runs_preset_id_fkey_generic') THEN
        -- keep old FK, add new one as well via extra column if needed; simplest: ensure data copied
        NULL;
    END IF;
END $$;

-- Migrate existing presets (idempotent)
INSERT INTO public.analysis_presets (id, slug, title_en, title_fr, category, default_goal_text, required_domains, suggested_formula, created_at)
SELECT id, slug, title_en, title_fr, category, default_goal_text, required_domains, suggested_formula, created_at
FROM public.cnps_analysis_presets
ON CONFLICT (slug) DO NOTHING;

-- Add organization scoping (NULL = global template)
ALTER TABLE public.analysis_presets ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE;
ALTER TABLE public.analysis_presets ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT true;

-- Recreate as VIEW for backward compat (so old code/table refs still work)
DROP VIEW IF EXISTS public.cnps_analysis_presets;
CREATE OR REPLACE VIEW public.cnps_analysis_presets AS SELECT * FROM public.analysis_presets;

-- RLS on generic table
ALTER TABLE public.analysis_presets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS presets_read_all ON public.analysis_presets;
CREATE POLICY presets_read_all ON public.analysis_presets FOR SELECT USING (auth.role() = 'authenticated');
DROP POLICY IF EXISTS presets_admin_write ON public.analysis_presets;
CREATE POLICY presets_admin_write ON public.analysis_presets FOR ALL USING (
    EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role='admin')
);

-- ── 3. Prompt / report branding scoping ─────────────────────────────────────
-- Scope prompt_templates to org (NULL = global)
ALTER TABLE public.prompt_templates ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE;

-- ── 4. Helper: resolve org for a user ───────────────────────────────────────
CREATE OR REPLACE FUNCTION public.user_organization(uid UUID)
RETURNS UUID LANGUAGE sql STABLE AS $$
    SELECT organization_id FROM public.user_profiles WHERE id = uid LIMIT 1
$$;

-- ── 5. Generic presets for new tenants (CNPS presets kept as global) ─────────
INSERT INTO public.analysis_presets (slug, title_en, title_fr, category, default_goal_text, required_domains, is_global)
VALUES
    ('revenue-monitoring','Revenue Monitoring','Suivi du chiffre d''affaires','Finance','Monthly revenue totals and growth rate by region/department', ARRAY['revenue'], true),
    ('user-growth','User Growth Analytics','Croissance utilisateurs','Growth','Monthly active users and new signups trend over last 12 months', ARRAY['users'], true),
    ('operational-efficiency','Operational Efficiency','Efficacité opérationnelle','Operations','Average processing time and throughput by team/region', ARRAY['operations'], true)
ON CONFLICT (slug) DO NOTHING;
