"""
Dependency Analyzer
===================
Before deleting any object, shows what depends on it.
Prevents unsafe deletions by analyzing impact.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    """Analyzes dependencies before deletion."""

    def __init__(self, db):
        self.db = db

    async def analyze_department(self, dept_id: str) -> dict:
        """Show what depends on a department."""
        deps = {
            "users": await self._count_users(dept_id),
            "kpis": await self._count_kpis(dept_id),
            "reports": await self._count_reports(dept_id),
            "anomalies": await self._count_anomalies(dept_id),
            "validation_logs": await self._count_validations(dept_id),
            "forecasts": await self._count_forecasts(dept_id),
        }

        warnings = []
        if deps["users"] > 0:
            warnings.append(f"{deps['users']} users assigned to this department")
        if deps["kpis"] > 0:
            warnings.append(f"{deps['kpis']} KPI records depend on this department")
        if deps["reports"] > 0:
            warnings.append(f"{deps['reports']} reports generated for this department")
        if deps["anomalies"] > 0:
            warnings.append(f"{deps['anomalies']} anomaly records exist")

        can_delete = deps["users"] == 0

        return {
            "entity_type": "department",
            "entity_id": dept_id,
            "dependencies": deps,
            "can_delete": can_delete,
            "warnings": warnings,
            "recommendation": (
                "Safe to delete" if can_delete
                else "Remove users first before deleting this department"
            ),
        }

    async def analyze_semantic_template(self, template_id: str) -> dict:
        """Show what depends on a semantic template."""
        deps = {
            "fields": await self._count_fields(template_id),
            "departments_using": await self._count_departments_using_template(template_id),
            "mappings": await self._count_mappings_for_template(template_id),
        }

        warnings = []
        if deps["departments_using"] > 0:
            warnings.append(f"{deps['departments_using']} departments use this template")
        if deps["fields"] > 0:
            warnings.append(f"{deps['fields']} field definitions will be deleted")
        if deps["mappings"] > 0:
            warnings.append(f"{deps['mappings']} field mappings will be affected")

        can_delete = deps["departments_using"] == 0

        return {
            "entity_type": "semantic_template",
            "entity_id": template_id,
            "dependencies": deps,
            "can_delete": can_delete,
            "warnings": warnings,
            "recommendation": (
                "Safe to delete" if can_delete
                else "Reassign departments to another template first"
            ),
        }

    async def analyze_instance_template(self, template_id: str) -> dict:
        """Show what depends on an instance template."""
        deps = {
            "departments_using": await self._count_departments_using_instance(template_id),
        }

        warnings = []
        if deps["departments_using"] > 0:
            warnings.append(f"{deps['departments_using']} departments use this template")

        can_delete = deps["departments_using"] == 0

        return {
            "entity_type": "instance_template",
            "entity_id": template_id,
            "dependencies": deps,
            "can_delete": can_delete,
            "warnings": warnings,
            "recommendation": (
                "Safe to delete" if can_delete
                else "Unassign departments before deleting"
            ),
        }

    async def analyze_user(self, user_id: str) -> dict:
        """Show what a user owns or is assigned to."""
        deps = {
            "kpi_results": await self._count_user_kpis(user_id),
            "reports": await self._count_user_reports(user_id),
            "snapshots": await self._count_user_snapshots(user_id),
            "analysis_runs": await self._count_user_analyses(user_id),
        }

        warnings = []
        total = sum(deps.values())
        if total > 0:
            warnings.append(f"User has {total} associated records that may become orphaned")

        return {
            "entity_type": "user",
            "entity_id": user_id,
            "dependencies": deps,
            "can_delete": True,  # Users can always be unassigned
            "warnings": warnings,
            "recommendation": "User role can be safely removed. Associated data will be preserved.",
        }

    # ── Private count helpers ────────────────────────────────────────────

    def _count_query(self, table: str, column: str, value: str) -> int:
        """Run a count query and return the count."""
        try:
            result = (
                self.db.table(table)
                .select("id", count="exact")
                .eq(column, value)
                .execute()
            )
            return getattr(result, "count", 0) or 0
        except Exception:
            return 0

    async def _count_users(self, dept_id: str) -> int:
        return self._count_query("user_roles", "department_id", dept_id)

    async def _count_kpis(self, dept_id: str) -> int:
        return self._count_query("kpi_results", "department_id", dept_id)

    async def _count_reports(self, dept_id: str) -> int:
        return self._count_query("daily_reports", "department_id", dept_id)

    async def _count_anomalies(self, dept_id: str) -> int:
        return self._count_query("anomaly_records", "department_id", dept_id)

    async def _count_validations(self, dept_id: str) -> int:
        return self._count_query("validation_logs", "department_id", dept_id)

    async def _count_forecasts(self, dept_id: str) -> int:
        return self._count_query("kpi_forecasts", "department_id", dept_id)

    async def _count_fields(self, template_id: str) -> int:
        return self._count_query("semantic_fields", "template_id", template_id)

    async def _count_departments_using_template(self, template_id: str) -> int:
        return self._count_query("departments", "template_id", template_id)

    async def _count_departments_using_instance(self, template_id: str) -> int:
        return self._count_query("departments", "instance_template_id", template_id)

    async def _count_mappings_for_template(self, template_id: str) -> int:
        try:
            field_ids_result = (
                self.db.table("semantic_fields")
                .select("id")
                .eq("template_id", template_id)
                .execute()
            )
            field_ids = [f["id"] for f in (field_ids_result.data or [])]
            if not field_ids:
                return 0
            result = (
                self.db.table("field_mappings")
                .select("id", count="exact")
                .in_("template_field_id", field_ids)
                .execute()
            )
            return getattr(result, "count", 0) or 0
        except Exception:
            return 0

    async def _count_user_kpis(self, user_id: str) -> int:
        return self._count_query("kpi_results", "user_id", user_id)

    async def _count_user_reports(self, user_id: str) -> int:
        return self._count_query("daily_reports", "user_id", user_id)

    async def _count_user_snapshots(self, user_id: str) -> int:
        return self._count_query("insight_snapshots", "user_id", user_id)

    async def _count_user_analyses(self, user_id: str) -> int:
        return self._count_query("analysis_runs", "user_id", user_id)
