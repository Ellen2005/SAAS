"""
Automated Migration Runner for Startup
Uses psycopg2 for direct SQL execution against Supabase PostgreSQL.
Falls back to Supabase RPC if direct connection is not available.
"""
import os
import re
import logging
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
MIGRATION_PATTERN = re.compile(r'^(\d{3})_(.+)\.sql$')


def get_migration_files() -> List[Tuple[str, str, Path]]:
    """Get all migration files sorted by version number."""
    migrations = []
    for path in MIGRATIONS_DIR.glob("*.sql"):
        match = MIGRATION_PATTERN.match(path.name)
        if match:
            version = match.group(1)
            name = match.group(2)
            migrations.append((version, name, path))
    migrations.sort(key=lambda x: int(x[0]))
    return migrations


def get_pg_connection():
    """Get a psycopg2 connection to Supabase PostgreSQL directly."""
    db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        return None
    try:
        import psycopg2
        conn = psycopg2.connect(db_url, connect_timeout=10)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.warning(f"psycopg2 connection failed: {e}")
        return None


def parse_migration_sql(sql: str) -> List[str]:
    """Split a migration SQL file into individual statements."""
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    statements = []
    current = []
    in_function = False
    dollar_quote = None

    for line in sql.split('\n'):
        stripped = line.strip()
        current.append(line)

        if '$$' in line:
            if dollar_quote is None:
                idx = line.index('$$')
                dollar_quote = line[idx:idx + 2]
                in_function = True
            elif dollar_quote in line:
                dollar_quote = None
                in_function = False

        if not in_function and stripped.endswith(';'):
            stmt = '\n'.join(current).strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt)
            current = []

    if current:
        stmt = '\n'.join(current).strip()
        if stmt:
            statements.append(stmt)

    return [s for s in statements if s.strip()]


def apply_migration_psycopg2(conn, version: str, name: str, sql: str) -> bool:
    """Apply a migration using psycopg2 direct connection."""
    import psycopg2
    statements = parse_migration_sql(sql)
    cursor = conn.cursor()

    for i, stmt in enumerate(statements):
        if not stmt.strip():
            continue
        try:
            cursor.execute(stmt)
            logger.debug(f"Migration {version} statement {i + 1}/{len(statements)} OK")
        except psycopg2.errors.DuplicateTable:
            logger.debug(f"Migration {version} statement {i + 1} - already exists, skipping")
        except psycopg2.errors.DuplicateFunction:
            logger.debug(f"Migration {version} statement {i + 1} - function already exists, skipping")
        except psycopg2.errors.DuplicateObject:
            logger.debug(f"Migration {version} statement {i + 1} - object already exists, skipping")
        except psycopg2.errors.DuplicatePolicy:
            logger.debug(f"Migration {version} statement {i + 1} - policy already exists, skipping")
        except psycopg2.errors.DuplicateSchema:
            logger.debug(f"Migration {version} statement {i + 1} - schema already exists, skipping")
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg or "duplicate" in err_msg:
                logger.debug(f"Migration {version} statement {i + 1} - already exists")
            else:
                logger.error(f"Migration {version} statement {i + 1} failed: {e}")
                cursor.close()
                return False

    cursor.close()
    return True


def apply_migration_supabase(version: str, name: str, sql: str) -> bool:
    """Apply a migration using Supabase RPC (requires exec_sql function)."""
    from ..core.supabase_client import get_supabase
    supabase = get_supabase()
    statements = parse_migration_sql(sql)

    for i, stmt in enumerate(statements):
        if not stmt.strip():
            continue
        try:
            supabase.rpc("exec_sql", {"sql": stmt}).execute()
            logger.debug(f"Migration {version} statement {i + 1}/{len(statements)} OK")
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg or "duplicate" in err_msg:
                logger.debug(f"Migration {version} statement {i + 1} - already exists")
            else:
                logger.error(f"Migration {version} statement {i + 1} failed: {e}")
                return False
    return True


def ensure_schema_migrations_pg(conn):
    """Create schema_migrations table if it doesn't exist (psycopg2)."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(10) PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cursor.close()


def get_applied_pg(conn) -> set:
    """Get applied migration versions via psycopg2."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_migrations ORDER BY applied_at")
        rows = cursor.fetchall()
        cursor.close()
        return {row[0] for row in rows}
    except Exception:
        return set()


def get_applied_supabase() -> set:
    """Get applied migration versions via Supabase RPC."""
    from ..core.supabase_client import get_supabase
    supabase = get_supabase()
    try:
        result = supabase.table("schema_migrations").select("version").order("applied_at").execute()
        if result.data:
            return {row["version"] for row in result.data}
    except Exception:
        pass
    return set()


def record_migration_pg(conn, version: str, name: str):
    """Record a migration as applied via psycopg2."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO schema_migrations (version, name) VALUES (%s, %s) ON CONFLICT (version) DO NOTHING",
        (version, name)
    )
    cursor.close()


def record_migration_supabase(version: str, name: str):
    """Record a migration as applied via Supabase."""
    from ..core.supabase_client import get_supabase
    supabase = get_supabase()
    try:
        supabase.table("schema_migrations").insert({
            "version": version,
            "name": name,
        }).execute()
    except Exception as e:
        logger.error(f"Failed to record migration {version}: {e}")


async def auto_run_migrations_on_startup() -> Tuple[int, List[str]]:
    """
    Run all pending migrations on startup.
    Uses psycopg2 with SUPABASE_DB_URL when available.
    Falls back to Supabase RPC otherwise.
    """
    migrations = get_migration_files()
    if not migrations:
        logger.info("No migration files found")
        return 0, []

    pg_conn = get_pg_connection()
    use_pg = pg_conn is not None

    if use_pg:
        logger.info("Migration runner: using direct PostgreSQL connection")
        ensure_schema_migrations_pg(pg_conn)
        applied = get_applied_pg(pg_conn)
    else:
        logger.info("Migration runner: using Supabase RPC (requires exec_sql function)")
        applied = get_applied_supabase()

    logger.info(f"Found {len(migrations)} migration files, {len(applied)} already applied")

    applied_count = 0
    applied_versions = []

    for version, name, path in migrations:
        if version in applied:
            continue

        logger.info(f"Applying migration {version}: {name}")

        try:
            sql = path.read_text(encoding='utf-8')
            if use_pg:
                success = apply_migration_psycopg2(pg_conn, version, name, sql)
            else:
                success = apply_migration_supabase(version, name, sql)

            if success:
                if use_pg:
                    record_migration_pg(pg_conn, version, name)
                else:
                    record_migration_supabase(version, name)
                applied_count += 1
                applied_versions.append(version)
                logger.info(f"Migration {version} applied successfully")
            else:
                logger.error(f"Migration {version} failed, stopping")
                break
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {e}")
            break

    if pg_conn:
        pg_conn.close()

    logger.info(f"Applied {applied_count} migrations on startup")
    return applied_count, applied_versions


async def run_specific_migration(version: str) -> bool:
    """Run a specific migration by version number."""
    migrations = get_migration_files()
    pg_conn = get_pg_connection()

    for v, name, path in migrations:
        if v == version:
            logger.info(f"Running migration {v}: {name}")
            sql = path.read_text(encoding='utf-8')

            if pg_conn:
                ensure_schema_migrations_pg(pg_conn)
                success = apply_migration_psycopg2(pg_conn, v, name, sql)
                if success:
                    record_migration_pg(pg_conn, v, name)
                pg_conn.close()
            else:
                success = apply_migration_supabase(v, name, sql)
                if success:
                    record_migration_supabase(v, name)

            return success

    logger.error(f"Migration {version} not found")
    return False


async def get_migration_status() -> dict:
    """Get status of all migrations."""
    migrations = get_migration_files()
    pg_conn = get_pg_connection()

    if pg_conn:
        ensure_schema_migrations_pg(pg_conn)
        applied = get_applied_pg(pg_conn)
        pg_conn.close()
    else:
        applied = get_applied_supabase()

    return {
        "total": len(migrations),
        "applied": len(applied),
        "pending": len(migrations) - len(applied),
        "connection_type": "psycopg2" if pg_conn else "supabase_rpc",
        "migrations": [
            {
                "version": v,
                "name": n,
                "status": "applied" if v in applied else "pending",
            }
            for v, n, _ in migrations
        ]
    }
