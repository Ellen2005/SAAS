-- Relax database_connections so Direct-URI-only saves work and long URIs fit.

ALTER TABLE public.database_connections
  ALTER COLUMN host DROP NOT NULL,
  ALTER COLUMN port DROP NOT NULL,
  ALTER COLUMN db_name DROP NOT NULL;

ALTER TABLE public.database_connections
  ALTER COLUMN host SET DEFAULT 'direct',
  ALTER COLUMN port SET DEFAULT 0,
  ALTER COLUMN db_name SET DEFAULT 'default';

ALTER TABLE public.database_connections
  ALTER COLUMN credentials TYPE TEXT;
