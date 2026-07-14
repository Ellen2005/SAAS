-- =============================================================================
-- BOOTSTRAP SCRIPT
-- Run this ONCE in Supabase SQL Editor to enable auto-migration
-- Go to: https://supabase.com/dashboard → SQL Editor → New Query → Paste → Run
-- =============================================================================

-- 1. Create exec_sql function (enables Supabase RPC-based migrations)
CREATE OR REPLACE FUNCTION public.exec_sql(sql TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE sql;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Create schema_migrations tracking table
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version VARCHAR(10) PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Mark bootstrap as applied
INSERT INTO public.schema_migrations (version, name)
VALUES ('020', 'critical_fixes')
ON CONFLICT (version) DO NOTHING;

-- 4. Create user_profiles table (if not exists from migration 009)
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email TEXT,
    display_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Enable RLS on user_profiles
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- 6. Create RLS policies for user_profiles
DO $$ BEGIN
    CREATE POLICY "Users can read own profile" ON public.user_profiles
        FOR SELECT USING (auth.uid() = id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Users can update own profile" ON public.user_profiles
        FOR UPDATE USING (auth.uid() = id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Users can insert own profile" ON public.user_profiles
        FOR INSERT WITH CHECK (auth.uid() = id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Admins can read all profiles" ON public.user_profiles
        FOR SELECT USING (
            EXISTS (
                SELECT 1 FROM public.user_roles
                WHERE user_id = auth.uid()
                AND role = 'admin'
            )
        );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Done! All migrations will now run automatically on next deploy.
