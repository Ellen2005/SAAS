"""Helpers for normalizing customer database connection payloads."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def detect_db_type(credentials: str, explicit: str | None = None) -> str:
    if explicit:
        normalized = explicit.lower().strip()
        if normalized in {"sqlserver", "mssql", "microsoft sql server"}:
            return "sqlserver"
        return normalized
    if not credentials:
        return "postgresql"
    lowered = credentials.lower().strip()
    if lowered.startswith("mongodb") or lowered.startswith("mongodb+srv"):
        return "mongodb"
    if lowered.startswith("sqlite"):
        return "sqlite"
    if "mysql" in lowered or lowered.startswith("mariadb"):
        return "mysql"
    if "mssql" in lowered or "sqlserver" in lowered:
        return "sqlserver"
    return "postgresql"


def normalize_credentials(credentials: str, db_type: str) -> str:
    """Ensure SQLAlchemy-friendly driver prefixes where needed."""
    if not credentials:
        return credentials
    cred = credentials.strip()
    lowered = cred.lower()
    if db_type == "mongodb":
        return cred
    if db_type == "sqlite":
        return cred if lowered.startswith("sqlite") else f"sqlite:///{cred.lstrip('/')}"
    if db_type == "mysql" and not lowered.startswith("mysql+"):
        if lowered.startswith("mysql://"):
            return cred.replace("mysql://", "mysql+pymysql://", 1)
        return f"mysql+pymysql://{cred.split('://', 1)[-1]}" if "://" not in cred else cred
    if db_type == "sqlserver" and not lowered.startswith("mssql"):
        if lowered.startswith("mssql+"):
            return cred
        return f"mssql+pymssql://{cred.split('://', 1)[-1]}" if "://" not in cred else cred
    if db_type == "postgresql" and lowered.startswith("postgres://"):
        return cred.replace("postgres://", "postgresql://", 1)
    if db_type == "postgresql" and lowered.startswith("postgresql://") and "+" not in lowered.split("://", 1)[0]:
        return cred.replace("postgresql://", "postgresql+psycopg2://", 1)
    return cred


def parse_connection_uri(credentials: str) -> dict[str, Any]:
    """Extract host/port/database from a connection URI for Supabase storage columns."""
    if not credentials:
        return {"host": "direct", "port": 0, "db_name": "default"}
    lowered = credentials.lower().strip()
    if lowered.startswith("sqlite"):
        path = credentials.split("///", 1)[-1] if "///" in credentials else credentials.split(":///", 1)[-1]
        return {"host": "local", "port": 0, "db_name": path or "sqlite"}
    if lowered.startswith("mongodb"):
        parsed = urlparse(credentials)
        db_name = (parsed.path or "").lstrip("/") or "admin"
        host = parsed.hostname or "cluster"
        port = parsed.port or 27017
        return {"host": host, "port": port, "db_name": db_name}
    parsed = urlparse(credentials)
    return {
        "host": parsed.hostname or "direct",
        "port": parsed.port or _default_port(lowered),
        "db_name": (parsed.path or "").lstrip("/") or "postgres",
    }


def _default_port(credentials_lower: str) -> int:
    if credentials_lower.startswith("mysql"):
        return 3306
    if "mssql" in credentials_lower:
        return 1433
    return 5432


def enrich_connection_payload(payload: dict) -> dict:
    """Fill missing host/port/db_name/credentials and normalize drivers."""
    credentials = (payload.get("credentials") or "").strip()
    db_type = detect_db_type(credentials, payload.get("db_type"))
    credentials = normalize_credentials(credentials, db_type)
    parsed = parse_connection_uri(credentials)

    host = (payload.get("host") or "").strip() or parsed["host"]
    port = payload.get("port")
    if port in (None, "", 0):
        port = parsed["port"]
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = parsed["port"]

    db_name = (payload.get("db_name") or "").strip() or parsed["db_name"]

    return {
        **payload,
        "db_type": db_type,
        "credentials": credentials,
        "host": host,
        "port": port,
        "db_name": db_name,
    }


def sqlalchemy_engine_kwargs(credentials: str, db_type: str) -> dict:
    """Dialect-specific create_engine kwargs."""
    if db_type == "sqlite":
        return {"pool_pre_ping": True}
    if db_type == "mysql":
        # Some public/legacy MySQL servers use older SSL that causes WRONG_VERSION_NUMBER.
        # Disable SSL for MySQL by default; users can enable it via connection_options.
        return {
            "connect_args": {"connect_timeout": 10, "ssl_disabled": True},
            "pool_pre_ping": True,
        }
    return {"connect_args": {"connect_timeout": 10}, "pool_pre_ping": True}
