-- =============================================================================
-- CNPS regional offices + department linkage
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.regional_offices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE public.departments
    ADD COLUMN IF NOT EXISTS regional_office_id UUID REFERENCES public.regional_offices(id) ON DELETE SET NULL;

ALTER TABLE public.user_roles
    ADD COLUMN IF NOT EXISTS job_title VARCHAR(120);

INSERT INTO public.regional_offices (code, name)
VALUES
    ('DOU', 'Douala Regional Office'),
    ('YAO', 'Yaoundé Regional Office'),
    ('BUE', 'Buéa Regional Office'),
    ('GAR', 'Garoua Regional Office'),
    ('BAF', 'Bafoussam Regional Office')
ON CONFLICT (code) DO NOTHING;
