"""
Audit Service
=============
Centralized audit logging for all system actions.
Tracks who did what, when, from where, and what changed.

Backward compatible: log_config_change() is preserved.
New code should use AuditService for richer audit trails.
"""
from datetime import datetime, timezone
import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)
UTC = timezone.utc


# ── Legacy function (preserved for backward compatibility) ────────────────────
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
            "created_at": datetime.now(UTC).isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log write failed (non-critical): {e}")


# ── New Audit Service ────────────────────────────────────────────────────────

class AuditService:
    """
    Centralized audit logging service.
    Every significant action in the system should go through this service.
    """

    def __init__(self, db):
        self.db = db

    async def log(
        self,
        *,
        user_id: str,
        action: str,
        entity: str,
        entity_id: Optional[str] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        changes: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
        duration_ms: Optional[int] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Write an audit record. Non-critical — failures are logged but never raised.
        
        Actions: CREATE, UPDATE, DELETE, LOGIN, LOGOUT, QUERY, TRIGGER,
                 EXPORT, DEPLOY, ASSIGN, REMOVE, ROLLBACK
        Entities: department, user_role, semantic_template, semantic_field,
                  instance_template, connection, preferences, nlq_query,
                  analysis, report, export, webhook, etl, ai_request
        """
        record = {
            "user_id": user_id,
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
            "old_value": old_value,
            "new_value": new_value,
            "changes": changes or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "reason": reason,
            "duration_ms": duration_ms,
            "request_id": request_id or str(uuid.uuid4())[:8],
            "created_at": datetime.now(UTC).isoformat(),
        }
        try:
            self.db.table("audit_logs").insert(record).execute()
        except Exception as e:
            logger.warning(f"Audit log write failed (non-critical): {e}")

    async def get_trail(
        self,
        *,
        entity: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        """
        Query audit trail with optional filters.
        Returns list of audit records, newest first.
        """
        try:
            query = self.db.table("audit_logs").select("*")
            if entity:
                query = query.eq("entity", entity)
            if entity_id:
                query = query.eq("entity_id", entity_id)
            if user_id:
                query = query.eq("user_id", user_id)
            if action:
                query = query.eq("action", action)
            result = (
                query
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return result.data if hasattr(result, "data") else []
        except Exception as e:
            logger.warning(f"Audit trail query failed: {e}")
            return []

    async def get_entity_history(self, entity: str, entity_id: str) -> list:
        """Get full change history for a specific entity."""
        return await self.get_trail(entity=entity, entity_id=entity_id, limit=50)

    async def get_user_actions(self, user_id: str, limit: int = 50) -> list:
        """Get recent actions by a specific user."""
        return await self.get_trail(user_id=user_id, limit=limit)

    async def get_stats(self, days: int = 30) -> dict:
        """Get audit statistics for the admin dashboard."""
        try:
            from datetime import timedelta
            since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
            result = (
                self.db.table("audit_logs")
                .select("action, entity, created_at")
                .gte("created_at", since)
                .execute()
            )
            records = result.data if hasattr(result, "data") else []

            by_action = {}
            by_entity = {}
            for r in records:
                action = r.get("action", "unknown")
                entity = r.get("entity", "unknown")
                by_action[action] = by_action.get(action, 0) + 1
                by_entity[entity] = by_entity.get(entity, 0) + 1

            return {
                "total_actions": len(records),
                "by_action": by_action,
                "by_entity": by_entity,
                "period_days": days,
            }
        except Exception as e:
            logger.warning(f"Audit stats query failed: {e}")
            return {"total_actions": 0, "by_action": {}, "by_entity": {}, "period_days": days}
