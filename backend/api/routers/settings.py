from fastapi import APIRouter, Depends, HTTPException
from ..core.supabase_client import get_supabase
from ..core.auth import require_role, resolve_user_id
from ..services.audit_service import log_config_change
from ..services.email_service import verify_unsubscribe_token
from ..services.connection_utils import (
    detect_db_type,
    enrich_connection_payload,
    normalize_credentials,
    sqlalchemy_engine_kwargs,
)
from ..services.etl_service import _get_free_local_port, _replace_db_url_host_port, _start_ssh_tunnel
from sqlalchemy import create_engine
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings/preferences")
def get_user_preferences(user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    defaults = {"ai_tone": "insight-driven", "sync_time": "02:00", "last_sync_status": "IDLE"}
    try:
        response = supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
        if hasattr(response, "data") and response.data:
            return response.data[0]
        return defaults
    except Exception as e:
        err = str(e).lower()
        if any(k in err for k in ("getaddrinfo", "connect", "network", "timeout", "disconnected", "eof")):
            return {**defaults, "warning": "Cannot reach Supabase — using defaults."}
        return {**defaults, "warning": f"Preferences unavailable: {str(e)[:120]}"}


@router.post("/settings/preferences")
def update_user_preferences(prefs: dict, context: dict = Depends(require_role(["manager", "admin"]))):
    user_id = context["user_id"]

    supabase = get_supabase()
    data = {
        "user_id": user_id,
        "ai_tone": prefs.get("ai_tone", "insight-driven"),
        "sync_time": prefs.get("sync_time", "02:00"),
        "sync_frequency": prefs.get("sync_frequency", "daily"),
        "yearly_date": prefs.get("yearly_date", "01-01"),
        "analysis_instruction": prefs.get("analysis_instruction"),
    }
    try:
        supabase.table("user_preferences").upsert(data, on_conflict="user_id").execute()
    except Exception as e:
        if any(k in str(e) for k in ("sync_frequency", "yearly_date", "analysis_instruction")):
            legacy = {k: v for k, v in data.items() if k not in {"sync_frequency", "yearly_date", "analysis_instruction"}}
            supabase.table("user_preferences").upsert(legacy, on_conflict="user_id").execute()
        else:
            raise

    log_config_change(supabase, user_id, "update", "preferences", {k: v for k, v in data.items() if k != "user_id"})
    return {"status": "success", "preferences": data}


@router.post("/test-connection")
def test_db_connection(connection_data: dict, context: dict = Depends(require_role(["manager", "admin"]))):
    enriched = enrich_connection_payload(connection_data)
    db_url = enriched.get("credentials")
    connection_method = enriched.get("connection_method") or "direct"
    connection_options = enriched.get("connection_options") or connection_data.get("connection_options") or {}
    db_type = enriched.get("db_type") or detect_db_type(db_url or "", connection_data.get("db_type"))
    if not db_url:
        raise HTTPException(status_code=400, detail="Missing connection string (credentials)")

    if db_type == "mongodb":
        try:
            import pymongo
            client = pymongo.MongoClient(db_url, serverSelectionTimeoutMS=8000)
            client.admin.command("ping")
            return {"status": "success", "message": "MongoDB connection verified!"}
        except ImportError:
            return {"status": "error", "message": "pymongo not installed. Run: pip install pymongo"}
        except Exception as e:
            return {"status": "error", "message": f"MongoDB Error: {str(e)}"}

    engine = None
    tunnel_proc = None
    try:
        db_url_for_test = db_url
        if connection_method == "ssh_tunnel":
            ssh_host = connection_options.get("ssh_host") or connection_data.get("host")
            ssh_user = connection_options.get("ssh_user")
            remote_host = connection_options.get("remote_db_host") or connection_data.get("host")
            remote_port = connection_data.get("port")
            if not all([ssh_host, ssh_user, remote_host, remote_port]):
                raise HTTPException(status_code=400, detail="SSH tunnel test requires SSH host, user, remote DB host, and port.")
            local_port = _get_free_local_port()
            tunnel_proc = _start_ssh_tunnel(ssh_host=str(ssh_host), ssh_user=str(ssh_user), remote_host=str(remote_host), remote_port=int(remote_port), local_port=int(local_port))
            db_url_for_test = _replace_db_url_host_port(db_url, "127.0.0.1", int(local_port))

        engine = create_engine(
            normalize_credentials(db_url_for_test, db_type),
            **sqlalchemy_engine_kwargs(db_url_for_test, db_type),
        )
        with engine.connect() as conn:
            from sqlalchemy import text
            if db_type == "oracle":
                conn.execute(text("SELECT 1 FROM DUAL"))
            else:
                conn.execute(text("SELECT 1"))
        return {"status": "success", "message": "Connection verified!"}
    except Exception as e:
        import traceback
        err_msg = str(e)
        logger.error("test-connection failed", exc_info=True)
        # Sanitize error message to prevent leaking sensitive details
        safe_err = "Database connection failed. Please check your connection details."
        if "ORA-01109" in err_msg:
            safe_err = (
                "Connection failed: Oracle PDB is not OPEN. "
                "Run this in SQL*Plus as sysdba:\n"
                "  ALTER PLUGGABLE DATABASE ORCLPDB OPEN;\n"
                "  ALTER PLUGGABLE DATABASE ORCLPDB SAVE STATE;"
            )
        return {"status": "error", "message": safe_err}
    finally:
        if engine is not None:
            try:
                engine.dispose()
            except Exception as e:
                logger.debug(f"Engine dispose failed (non-critical): {e}")
        if tunnel_proc is not None:
            try:
                tunnel_proc.terminate()
                tunnel_proc.wait(timeout=5)
            except Exception:
                try:
                    tunnel_proc.kill()
                except Exception as e:
                    logger.debug(f"Tunnel kill also failed (non-critical): {e}")


@router.post("/settings/connection")
def save_db_connection(conn_data: dict, context: dict = Depends(require_role(["manager", "admin"]))):
    user_id = context["user_id"]

    enriched = enrich_connection_payload(conn_data)
    if not enriched.get("credentials"):
        raise HTTPException(status_code=400, detail="Missing connection string (credentials)")

    from ..services.connection_crypto import encrypt_credentials
    stored_credentials = encrypt_credentials(enriched.get("credentials"))

    supabase = get_supabase()
    data = {
        "user_id": user_id,
        "db_type": enriched.get("db_type", "postgresql"),
        "host": enriched.get("host") or "direct",
        "port": enriched.get("port") if enriched.get("port") is not None else 0,
        "db_name": enriched.get("db_name") or "default",
        "credentials": stored_credentials,
        "read_only": True,
        "connection_method": enriched.get("connection_method", "direct"),
        "connection_options": enriched.get("connection_options"),
    }
    try:
        existing = supabase.table("database_connections").select("id").eq("user_id", user_id).limit(1).execute()
        has_existing = bool(getattr(existing, "data", None))
        if has_existing:
            supabase.table("database_connections").update(data).eq("user_id", user_id).execute()
        else:
            supabase.table("database_connections").insert(data).execute()
    except Exception as e:
        err = str(e)
        if "connection_method" in err or "connection_options" in err:
            legacy = {k: v for k, v in data.items() if k not in {"connection_method", "connection_options"}}
            existing = supabase.table("database_connections").select("id").eq("user_id", user_id).limit(1).execute()
            if bool(getattr(existing, "data", None)):
                supabase.table("database_connections").update(legacy).eq("user_id", user_id).execute()
            else:
                supabase.table("database_connections").insert(legacy).execute()
        elif "value too long" in err.lower() or "character varying" in err.lower():
            raise HTTPException(
                status_code=500,
                detail=(
                    "Connection string is too long for the current database schema. "
                    "Run backend/migrations/006_fix_database_connections.sql in Supabase SQL Editor, then retry."
                ),
            ) from e
        else:
            logger.error(f"Failed to save connection: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to save connection.") from e

    log_config_change(supabase, user_id, "update", "connection", {"db_type": data["db_type"], "host": data["host"], "connection_method": data["connection_method"]})
    return {"status": "success", "message": "Connection details saved successfully."}


@router.get("/unsubscribe")
def unsubscribe(email: str, token: str):
    if not verify_unsubscribe_token(email, token):
        raise HTTPException(status_code=400, detail="Invalid or expired unsubscribe link.")
    supabase = get_supabase()
    try:
        supabase.table("notification_recipients").delete().eq("email", email).execute()
        return {"status": "unsubscribed", "email": email}
    except Exception as e:
        logger.error(f"Unsubscribe error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to unsubscribe.")
