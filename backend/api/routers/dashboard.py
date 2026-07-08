from fastapi import APIRouter, Depends
from typing import List, Optional
from ..core.supabase_client import get_supabase
from ..core.auth import resolve_user_id
from ..core.utils import safe_data
from ..services.cache_service import get_cached, set_cached
from ..core.constants import LEGACY_DEMO_KPI_NAMES, is_legacy_demo_kpi as _is_legacy_demo_kpi, is_legacy_demo_report as _is_legacy_demo_report
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

INSTITUTION_NAME = os.getenv("INSTITUTION_NAME", "Smart Analytics")

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_summary(user_id: str = Depends(resolve_user_id)):
    cache_key_str = f"v1:summary:{user_id}"
    cached = get_cached(cache_key_str)
    if cached:
        return cached
    
    supabase = get_supabase()
    try:
        def fetch_kpis():
            return supabase.table("kpi_results").select("*").eq("user_id", user_id).order("recorded_at", desc=True).limit(50).execute()
        def fetch_anomalies():
            return supabase.table("anomaly_records").select("*").eq("user_id", user_id).order("detected_at", desc=True).limit(25).execute()
        def fetch_reports():
            return supabase.table("daily_reports").select("*").eq("user_id", user_id).order("report_date", desc=True).limit(5).execute()
        def fetch_validations():
            return supabase.table("validation_logs").select("check_type, status, message, details").eq("user_id", user_id).order("created_at", desc=True).limit(20).execute()
        def fetch_analysis():
            return supabase.table("analysis_runs").select("*").eq("user_id", user_id).eq("status", "completed").order("completed_at", desc=True).limit(3).execute()

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(fetch_kpis): "kpi",
                pool.submit(fetch_anomalies): "anomaly",
                pool.submit(fetch_reports): "report",
                pool.submit(fetch_validations): "validation",
                pool.submit(fetch_analysis): "analysis",
            }
            results = {}
            for future in as_completed(futures):
                try:
                    results[futures[future]] = future.result()
                except Exception as e:
                    logger.warning(f"Parallel fetch {futures[future]} failed: {e}")
                    results[futures[future]] = None

        kpi_resp = results.get("kpi")
        anomaly_resp = results.get("anomaly")
        report_resp = results.get("report")
        validation_resp = results.get("validation")
        analysis_resp = results.get("analysis")

        kpis = []
        if kpi_resp and hasattr(kpi_resp, "data") and kpi_resp.data:
            seen_kpis = set()
            for item in kpi_resp.data:
                kpi_name = str(item.get("kpi_name", "unknown"))
                if _is_legacy_demo_kpi(item) or kpi_name in seen_kpis:
                    continue
                val = item.get("value")
                try:
                    num_val = float(val) if val is not None else 0
                except (TypeError, ValueError):
                    num_val = 0
                if num_val == 0 and item.get("status") in (None, "", "NORMAL"):
                    continue
                seen_kpis.add(kpi_name)
                try:
                    kpis.append({
                        "id": str(item.get("id", "")),
                        "kpi_name": kpi_name,
                        "value": num_val,
                        "dod_pct": float(item["dod_pct"]) if item.get("dod_pct") is not None else None,
                        "wow_pct": float(item["wow_pct"]) if item.get("wow_pct") is not None else None,
                        "avg_7d": float(item["avg_7d"]) if item.get("avg_7d") is not None else None,
                        "status": str(item.get("status") or "NORMAL"),
                        "recorded_at": str(item.get("recorded_at", "")),
                    })
                except (ValueError, TypeError) as parse_err:
                    logger.warning(f"KPI parse error: {parse_err} — row: {item}")

        anomalies = []
        if anomaly_resp and hasattr(anomaly_resp, "data") and anomaly_resp.data:
            for item in [row for row in anomaly_resp.data if not _is_legacy_demo_kpi(row)]:
                try:
                    anomalies.append({
                        "id": str(item.get("id", "")),
                        "kpi_name": str(item.get("kpi_name", "unknown")),
                        "severity": str(item.get("severity") or "WARNING"),
                        "deviation": float(item.get("deviation") or 0),
                        "context": item.get("context") or {},
                        "detected_at": str(item.get("detected_at", "")),
                    })
                except (ValueError, TypeError) as parse_err:
                    logger.warning(f"Anomaly parse error: {parse_err} — row: {item}")

        narrative = "No analytics report generated yet. Go to the Goal Analysis page to run your first analysis, or click Sync Now on the dashboard."
        last_refreshed = "Never"
        
        if report_resp and hasattr(report_resp, "data") and report_resp.data:
            reports = [row for row in report_resp.data if not _is_legacy_demo_report(row)]
            if reports:
                narrative = reports[0].get("narrative") or narrative
                last_refreshed = str(reports[0]["report_date"])
        
        if narrative.startswith("No analytics") and hasattr(analysis_resp, "data") and analysis_resp.data:
            analysis = analysis_resp.data[0]
            analysis_date = analysis.get("completed_at", "")
            explanation = analysis.get("metrics_json", {}).get("explanation", {})
            overview = explanation.get("overview") or explanation.get("what_this_means") or ""
            goal = analysis.get("goal_text", "Analysis completed")
            result_summary = analysis.get("result_summary", "Analysis completed successfully.")
            row_count = analysis.get("metrics_json", {}).get("row_count", 0)
            narrative = (
                f"Latest Goal Analysis: {goal}\n\n"
                f"{overview or result_summary}"
            )
            if row_count:
                narrative += f"\n\nRows analyzed: {row_count}"
            last_refreshed = analysis_date[:10] if analysis_date else "Recent"

        summary_dict = {
            "kpis": kpis,
            "anomalies": anomalies,
            "narrative": narrative,
            "last_refreshed": last_refreshed,
        }
        validation_rows = validation_resp.data if hasattr(validation_resp, "data") and validation_resp.data else []
        filtered_validation_rows = []
        for row in validation_rows:
            msg = row.get("message") or ""
            if any(legacy.lower() in msg.lower() or legacy.replace("_", " ").lower() in msg.lower() for legacy in LEGACY_DEMO_KPI_NAMES):
                continue
            filtered_validation_rows.append(row)

        latest_by_type = {}
        for row in filtered_validation_rows:
            latest_by_type.setdefault(row.get("check_type"), row)
        summary_dict["validation"] = list(latest_by_type.values())
        try:
            from ..services.kpi_config import resolve_kpi_mode
            from ..services.chart_service import build_kpi_snapshot_chart
            summary_dict["kpi_mode"] = resolve_kpi_mode(supabase, user_id)
            summary_dict["snapshot_chart"] = build_kpi_snapshot_chart(kpis)
        except Exception:
            summary_dict["kpi_mode"] = {"mode": "auto"}
            summary_dict["snapshot_chart"] = None
        set_cached(cache_key_str, summary_dict, ttl=60)
        return summary_dict
    except Exception as e:
        logger.error(f"Summary Fetch Error: {e}", exc_info=True)
        return {"kpis": [], "anomalies": [], "narrative": "Unable to fetch dashboard summary.", "last_refreshed": "ERROR"}


@router.get("/kpis/series")
def get_kpi_series(user_id: str = Depends(resolve_user_id), limit: int = 120, days: int = None):
    cache_key_str = f"v1:kpi_series:{user_id}:{limit}:{days}"
    cached = get_cached(cache_key_str)
    if cached:
        return cached
    
    supabase = get_supabase()
    try:
        fetch_limit = min(800, max(50, limit * 10))
        query = (
            supabase.table("kpi_results")
            .select("kpi_name, value, recorded_at, source")
            .eq("user_id", user_id)
            .order("recorded_at", desc=True)
            .limit(fetch_limit)
        )
        
        if days and days > 0:
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            query = query.gte("recorded_at", cutoff_date)
        
        rows = query.execute()
        raw = rows.data if hasattr(rows, "data") and rows.data else []
        series: dict[str, list[dict]] = {}
        for row in raw:
            if _is_legacy_demo_kpi(row):
                continue
            name = str(row.get("kpi_name") or "unknown")
            series.setdefault(name, [])
            if len(series[name]) >= limit:
                continue
            series[name].append(
                {
                    "t": str(row.get("recorded_at") or ""),
                    "value": float(row.get("value") or 0),
                    "source": row.get("source") or "etl",
                }
            )
        for key in list(series.keys()):
            series[key] = list(reversed(series[key]))
        
        set_cached(cache_key_str, {"series": series}, ttl=60)
        return {"series": series}
    except Exception:
        logger.error("KPI series error", exc_info=True)
        return {"series": {}, "error": "Failed to fetch KPI series."}


@router.get("/dashboard/widgets")
def get_dashboard_widgets(user_id: str = Depends(resolve_user_id)):
    supabase = get_supabase()
    try:
        defs = supabase.table("kpi_definitions").select("*").order("sort_order").execute()
        widgets = defs.data if hasattr(defs, "data") and defs.data else []
    except Exception:
        widgets = []
    if not widgets:
        widgets = [
            {"name": "total_contributions", "display_name_en": "Total Contributions", "widget_type": "area"},
            {"name": "pension_disbursement", "display_name_en": "Pension Disbursement", "widget_type": "area"},
            {"name": "workplace_accident_frequency", "display_name_en": "AT/MP Frequency", "widget_type": "line"},
            {"name": "regional_contribution_share", "display_name_en": "Contributions by Region", "widget_type": "bar"},
        ]
    return {"widgets": widgets, "institution": INSTITUTION_NAME}


@router.get("/dashboard/regional")
def get_regional_data(user_id: str = Depends(resolve_user_id)):
    """Return per-region KPI values derived from kpi_results.
    Looks for KPI names that contain known CNPS region keywords, or falls back
    to grouping the latest KPI values by name and assigning them to regions."""
    REGION_KEYWORDS = {
        "douala": "Douala",
        "yaounde": "Yaoundé",
        "yaounde": "Yaoundé",
        "bafoussam": "Bafoussam",
        "garoua": "Garoua",
        "maroua": "Maroua",
        "bamenda": "Bamenda",
        "ebolowa": "Ebolowa",
        "bertoua": "Bertoua",
        "nanga": "Nanga-Eboko",
        "buea": "Buea",
    }
    supabase = get_supabase()
    try:
        rows = safe_data(
            supabase.table("kpi_results")
            .select("kpi_name, value, recorded_at")
            .eq("user_id", user_id)
            .order("recorded_at", desc=True)
            .limit(200)
            .execute()
        )
        # First pass: look for KPI names that contain region keywords
        region_map = {}
        for row in rows:
            name_lower = (row.get("kpi_name") or "").lower()
            for keyword, label in REGION_KEYWORDS.items():
                if keyword in name_lower and keyword not in region_map:
                    region_map[keyword] = {
                        "region_id": keyword,
                        "region_name": label,
                        "value": float(row.get("value") or 0),
                        "kpi_name": row.get("kpi_name"),
                    }
                    break

        # Second pass: if no region-named KPIs found, use latest unique KPIs
        # and assign them to regions by index (labelled clearly)
        if not region_map:
            seen = {}
            for row in rows:
                name = row.get("kpi_name") or ""
                if _is_legacy_demo_kpi(row) or name in seen:
                    continue
                seen[name] = float(row.get("value") or 0)

            region_ids = list(REGION_KEYWORDS.keys())
            region_labels = list(REGION_KEYWORDS.values())
            for i, (name, value) in enumerate(list(seen.items())[:10]):
                rid = region_ids[i % len(region_ids)]
                region_map[f"{rid}_{i}"] = {
                    "region_id": rid,
                    "region_name": region_labels[i % len(region_labels)],
                    "value": value,
                    "kpi_name": name,
                    "is_kpi_proxy": True,
                }

        return {"regions": list(region_map.values()), "source": "kpi_results"}
    except Exception:
        logger.error("Regional data error", exc_info=True)
        return {"regions": [], "error": "Failed to fetch regional data."}


@router.get("/forecasts")
def get_forecasts(user_id: str = Depends(resolve_user_id), days: int = None):
    supabase = get_supabase()
    try:
        query = (
            supabase.table("kpi_forecasts")
            .select("*")
            .eq("user_id", user_id)
            .order("forecast_date")
        )
        
        if days and days > 0:
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            query = query.gte("forecast_date", cutoff_date)
        
        rows = query.execute()
        raw = rows.data if hasattr(rows, "data") and rows.data else []
        filtered = [
            r
            for r in raw
            if r.get("kpi_name") not in LEGACY_DEMO_KPI_NAMES
            and r.get("kpi_name", "").replace("_", " ").title() not in LEGACY_DEMO_KPI_NAMES
        ]

        forecasts = []
        for f in filtered:
            forecasts.append(
                {
                    **f,
                    "kpi_name": f.get("kpi_name"),
                    "forecast_date": f.get("forecast_date"),
                    "predicted_value": f.get("predicted_value"),
                    "lower_bound": f.get("lower_bound"),
                    "upper_bound": f.get("upper_bound"),
                }
            )

        return {"forecasts": forecasts}
    except Exception:
        logger.error("Forecasts error", exc_info=True)
        return {"forecasts": [], "error": "Failed to fetch forecasts."}
