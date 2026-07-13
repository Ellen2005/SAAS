"""
Automated Migration Runner for Startup
Scans migration files and applies them in order to Supabase.
"""
import os
import re
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from ..core.supabase_client import get_supabase

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
MIGRATION_PATTERN = re.compile(r'^(\d{3})_(.+)\.sql$')


def get_migration_files() -> List[Tuple[str, str, Path]]:
    """
    Get all migration files sorted by version number.
    Returns list of (version, name, path).
    """
    migrations = []
    for path in MIGRATIONS_DIR.glob("*.sql"):
        match = MIGRATION_PATTERN.match(path.name)
        if match:
            version = match.group(1)
            name = match.group(2)
            migrations.append((version, name, path))
    
    # Sort by version number
    migrations.sort(key=lambda x: int(x[0]))
    return migrations


def get_applied_migrations(supabase) -> List[str]:
    """Get list of already applied migration versions."""
    try:
        result = supabase.table("schema_migrations").select("version").order("applied_at").execute()
        if result.data:
            return [row["version"] for row in result.data]
    except Exception as e:
        logger.warning(f"Could not fetch applied migrations: {e}")
    return []


def parse_migration_sql(sql: str) -> List[str]:
    """
    Split a migration SQL file into individual statements.
    Handles PostgreSQL-specific syntax.
    """
    # Remove comments
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    
    # Split by semicolon, but be careful with function definitions
    statements = []
    current = []
    in_function = False
    dollar_quote = None
    
    for line in sql.split('\n'):
        stripped = line.strip()
        current.append(line)
        
        # Track dollar-quoted strings (used in function bodies)
        if '$$' in line:
            if dollar_quote is None:
                dollar_quote = line[line.index('$$'):line.index('$$')+2]
                in_function = True
            elif dollar_quote in line:
                dollar_quote = None
                in_function = False
        
        # Check for semicolon at end of statement (not inside function)
        if not in_function and stripped.endswith(';'):
            stmt = '\n'.join(current).strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt)
            current = []
    
    # Add any remaining
    if current:
        stmt = '\n'.join(current).strip()
        if stmt:
            statements.append(stmt)
    
    return [s for s in statements if s.strip()]


async def apply_migration(supabase, version: str, name: str, sql: str) -> bool:
    """Apply a single migration."""
    statements = parse_migration_sql(sql)
    
    for i, stmt in enumerate(statements):
        if not stmt.strip():
            continue
        try:
            # Use rpc to execute raw SQL
            result = supabase.rpc("exec_sql", {"sql": stmt}).execute()
            logger.debug(f"Migration {version} statement {i+1}/{len(statements)} executed")
        except Exception as e:
            # Try direct table operations for common cases
            logger.error(f"Migration {version} statement {i+1} failed: {e}")
            return False
    
    # Record migration as applied
    try:
        supabase.table("schema_migrations").insert({
            "version": version,
            "name": name,
        }).execute()
        logger.info(f"Migration {version} ({name}) applied successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to record migration {version}: {e}")
        return False


async def auto_run_migrations_on_startup() -> Tuple[int, List[str]]:
    """
    Run all pending migrations on startup.
    Returns (applied_count, applied_versions).
    """
    supabase = get_supabase()
    
    # Get all migration files
    migrations = get_migration_files()
    if not migrations:
        logger.info("No migration files found")
        return 0, []
    
    # Get already applied
    applied = set(get_applied_migrations(supabase))
    logger.info(f"Found {len(migrations)} migration files, {len(applied)} already applied")
    
    # Apply pending
    applied_count = 0
    applied_versions = []
    
    for version, name, path in migrations:
        if version in applied:
            logger.debug(f"Skipping already applied migration {version}")
            continue
        
        logger.info(f"Applying migration {version}: {name}")
        
        try:
            sql = path.read_text(encoding='utf-8')
            success = await apply_migration(supabase, version, name, sql)
            if success:
                applied_count += 1
                applied_versions.append(version)
            else:
                logger.error(f"Migration {version} failed, stopping")
                break
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {e}")
            break
    
    logger.info(f"Applied {applied_count} migrations on startup")
    return applied_count, applied_versions


async def run_specific_migration(version: str) -> bool:
    """Run a specific migration by version number."""
    supabase = get_supabase()
    migrations = get_migration_files()
    
    for v, name, path in migrations:
        if v == version:
            logger.info(f"Running migration {v}: {name}")
            sql = path.read_text(encoding='utf-8')
            return await apply_migration(supabase, v, name, sql)
    
    logger.error(f"Migration {version} not found")
    return False


async def get_migration_status() -> dict:
    """Get status of all migrations."""
    supabase = get_supabase()
    migrations = get_migration_files()
    applied = set(get_applied_migrations(supabase))
    
    return {
        "total": len(migrations),
        "applied": len(applied),
        "pending": len(migrations) - len(applied),
        "migrations": [
            {
                "version": v,
                "name": n,
                "status": "applied" if v in applied else "pending",
                "file": str(p)
            }
            for v, n, p in migrations
        ]
    }