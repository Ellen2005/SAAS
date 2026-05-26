from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def log_config_change(supabase, user_id: str, action: str, entity: str, changes: dict):
    """
    Persist a configuration change to the audit_logs table.
    action: e.g. 'update', 'create', 'delete'
    entity: e.g. 'preferences', 'connection', 'mapping', 'role', 'department'
    changes: dict of what changed
    """
    try:
        supabase.table("audit_logs").insert({
            "user_id": user_id,
            "action": action,
            "entity": entity,
            "changes": changes,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log write failed (non-critical): {e}")
