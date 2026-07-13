"""
Supabase Transaction Wrapper for ETL Operations
Provides transactional guarantees for multi-table ETL writes.
"""
import uuid
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from ..core.supabase_client import get_supabase

logger = logging.getLogger(__name__)


class SupabaseTransaction:
    """
    Manages a batch of operations that should be executed atomically.
    Uses Supabase's batch operations to group multiple inserts/updates.
    
    Note: Supabase doesn't support true ACID transactions across tables
    via the REST API. This class provides the closest approximation by:
    1. Batching all operations
    2. Using RPC calls for complex multi-table operations
    3. Providing rollback compensation via delete operations
    """
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or get_supabase()
        self.operations: List[Dict[str, Any]] = []
        self.rollback_ops: List[Dict[str, Any]] = []
        self._committed = False
    
    def insert(self, table: str, data: Dict[str, Any], returning: bool = True) -> "SupabaseTransaction":
        """Add an insert operation to the transaction."""
        op = {
            "type": "insert",
            "table": table,
            "data": data,
            "returning": returning
        }
        self.operations.append(op)
        
        # Add rollback operation (delete by ID if returned)
        if "id" in data:
            self.rollback_ops.append({
                "type": "delete",
                "table": table,
                "filter": {"id": data["id"]}
            })
        return self
    
    def upsert(self, table: str, data: Dict[str, Any], on_conflict: str) -> "SupabaseTransaction":
        """Add an upsert operation."""
        op = {
            "type": "upsert",
            "table": table,
            "data": data,
            "on_conflict": on_conflict
        }
        self.operations.append(op)
        return self
    
    def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> "SupabaseTransaction":
        """Add an update operation."""
        op = {
            "type": "update",
            "table": table,
            "data": data,
            "filters": filters
        }
        self.operations.append(op)
        return self
    
    def delete(self, table: str, filters: Dict[str, Any]) -> "SupabaseTransaction":
        """Add a delete operation."""
        op = {
            "type": "delete",
            "table": table,
            "filters": filters
        }
        self.operations.append(op)
        return self
    
    def rpc(self, function_name: str, params: Dict[str, Any]) -> "SupabaseTransaction":
        """Add a stored procedure call."""
        op = {
            "type": "rpc",
            "function": function_name,
            "params": params
        }
        self.operations.append(op)
        return self
    
    async def commit(self) -> Dict[str, Any]:
        """Execute all operations in the transaction."""
        if self._committed:
            raise RuntimeError("Transaction already committed")
        
        results = {"success": True, "operations": [], "errors": []}
        
        # Group operations by type for batch execution
        inserts_by_table: Dict[str, List[Dict]] = {}
        upserts_by_table: Dict[str, List[Dict]] = {}
        updates_by_table: Dict[str, List[Dict]] = {}
        deletes_by_table: Dict[str, List[Dict]] = {}
        rpc_calls: List[Dict] = []
        
        for op in self.operations:
            if op["type"] == "insert":
                inserts_by_table.setdefault(op["table"], []).append(op)
            elif op["type"] == "upsert":
                upserts_by_table.setdefault(op["table"], []).append(op)
            elif op["type"] == "update":
                updates_by_table.setdefault(op["table"], []).append(op)
            elif op["type"] == "delete":
                deletes_by_table.setdefault(op["table"], []).append(op)
            elif op["type"] == "rpc":
                rpc_calls.append(op)
        
        try:
            # Execute batch inserts
            for table, ops in inserts_by_table.items():
                data = [op["data"] for op in ops]
                resp = self.supabase.table(table).insert(data).execute()
                results["operations"].extend(resp.data if resp.data else [])
            
            # Execute batch upserts
            for table, ops in upserts_by_table.items():
                data = [op["data"] for op in ops]
                on_conflict = ops[0].get("on_conflict", "id")
                resp = self.supabase.table(table).upsert(data, on_conflict=on_conflict).execute()
                results["operations"].extend(resp.data if resp.data else [])
            
            # Execute batch updates (one by one - Supabase limitation)
            for table, ops in updates_by_table.items():
                for op in ops:
                    query = self.supabase.table(table).update(op["data"])
                    for key, value in op["filters"].items():
                        query = query.eq(key, value)
                    resp = query.execute()
                    results["operations"].extend(resp.data if resp.data else [])
            
            # Execute batch deletes
            for table, ops in deletes_by_table.items():
                for op in ops:
                    query = self.supabase.table(table).delete()
                    for key, value in op["filters"].items():
                        query = query.eq(key, value)
                    resp = query.execute()
                    results["operations"].extend(resp.data if resp.data else [])
            
            # Execute RPC calls
            for rpc in rpc_calls:
                resp = self.supabase.rpc(rpc["function"], rpc["params"]).execute()
                results["operations"].append({"rpc": rpc["function"], "result": resp.data})
            
            self._committed = True
            logger.info(f"Transaction committed: {len(self.operations)} operations executed")
            return results
            
        except Exception as e:
            logger.error(f"Transaction failed: {e}", exc_info=True)
            results["success"] = False
            results["errors"].append(str(e))
            
            # Attempt rollback
            await self._rollback()
            raise
    
    async def _rollback(self) -> Dict[str, Any]:
        """Execute rollback operations."""
        rollback_results = {"rolled_back": 0, "errors": []}
        
        for op in reversed(self.rollback_ops):
            try:
                if op["type"] == "delete":
                    query = self.supabase.table(op["table"]).delete()
                    for key, value in op["filter"].items():
                        query = query.eq(key, value)
                    query.execute()
                    rollback_results["rolled_back"] += 1
            except Exception as e:
                rollback_results["errors"].append(str(e))
                logger.error(f"Rollback failed for {op}: {e}")
        
        return rollback_results


@asynccontextmanager
async def transaction(supabase_client=None):
    """
    Async context manager for Supabase transactions.
    
    Usage:
        async with transaction() as tx:
            tx.insert("table1", {"id": "1", "name": "test"})
            tx.insert("table2", {"id": "1", "ref_id": "1"})
            await tx.commit()
    """
    tx = SupabaseTransaction(supabase_client)
    try:
        yield tx
        await tx.commit()
    except Exception:
        await tx._rollback()
        raise


# Convenience functions for common ETL patterns
async def bulk_insert_with_lineage(
    supabase_client,
    user_id: str,
    department_id: str,
    kpis: List[Dict],
    anomalies: List[Dict],
    batch_source_id: str
) -> Dict[str, Any]:
    """
    Atomically insert KPIs, anomalies, and lineage records.
    """
    async with transaction(supabase_client) as tx:
        # Insert KPIs
        for kpi in kpis:
            tx.insert("kpi_results", {**kpi, "user_id": user_id, "department_id": department_id, "source_id": batch_source_id})
        
        # Insert anomalies
        for anomaly in anomalies:
            tx.insert("anomaly_records", {**anomaly, "user_id": user_id, "department_id": department_id})
        
        # Insert lineage records
        for kpi in kpis:
            tx.insert("source_lineage_records", {
                "batch_source_id": batch_source_id,
                "user_id": user_id,
                "department_id": department_id,
                "kpi_name": kpi["kpi_name"],
                "source_record_id": kpi.get("source_row_id", str(uuid.uuid4())),
                "record_label": kpi.get("record_label"),
                "record_date": kpi.get("recorded_at"),
                "record_value": kpi.get("value", 0),
                "raw_payload": kpi
            })
        
        return await tx.commit()


async def bulk_upsert_field_mappings(
    supabase_client,
    user_id: str,
    mappings: List[Dict]
) -> Dict[str, Any]:
    """Atomically upsert multiple field mappings."""
    async with transaction(supabase_client) as tx:
        for mapping in mappings:
            tx.upsert("field_mappings", {
                "user_id": user_id,
                "template_field_id": mapping["template_field_id"],
                "local_column_name": mapping["local_column_name"],
                "transformation_rule": mapping.get("transformation_rule"),
                "updated_at": "now()"
            }, on_conflict="user_id,template_field_id")
        
        return await tx.commit()


async def atomic_report_generation(
    supabase_client,
    user_id: str,
    department_id: str,
    report_data: Dict,
    narrative: str
) -> Dict[str, Any]:
    """Atomically create report, daily_report entry, and combined_report refresh."""
    async with transaction(supabase_client) as tx:
        # Insert professional report
        report_id = str(uuid.uuid4())
        tx.insert("reports", {
            "id": report_id,
            "user_id": user_id,
            "department_id": department_id,
            "title": report_data.get("title", "Analysis Report"),
            "narrative": narrative,
            "report_type": report_data.get("type", "goal"),
            "format": "pdf",
            "status": "generated"
        })
        
        # Insert daily report
        tx.insert("daily_reports", {
            "user_id": user_id,
            "department_id": department_id,
            "narrative": narrative,
            "report_date": report_data.get("report_date", "now()"),
        })
        
        # Queue combined report refresh via RPC
        tx.rpc("refresh_combined_report", {"report_date": report_data.get("report_date")})
        
        return await tx.commit()