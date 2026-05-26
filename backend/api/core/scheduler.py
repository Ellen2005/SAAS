import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from ..services.etl_service import run_user_etl_pipeline

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()

from ..core.supabase_client import get_supabase


def process_scheduled_etl():
    """
    Heartbeat job checking for frequency-based sync triggers.
    """
    from datetime import datetime

    now = datetime.now()
    now_hm = now.strftime("%H:%M")
    today_month_day = now.strftime("%m-%d")  # Format for yearly comparison
    is_monday = now.weekday() == 0
    is_first_of_month = now.day == 1

    supabase = get_supabase()

    # 1. Fetch all users who have their Sync Time scheduled for NOW
    try:
        response = (
            supabase.table("user_preferences")
            .select("*")
            .eq("sync_time", now_hm)
            .execute()
        )
    except Exception as e:
        logger.error(f"User preference heartbeat check failed: {e}")
        response = None

    if response and hasattr(response, "data") and response.data:
        for pref in response.data:
            user_id = pref["user_id"]
            freq = pref.get("sync_frequency", "daily").lower()
            y_date = pref.get("yearly_date", "01-01")

            should_trigger = False

            if freq == "daily":
                should_trigger = True
            elif freq == "weekly" and is_monday:
                should_trigger = True
            elif freq == "monthly" and is_first_of_month:
                should_trigger = True
            elif freq == "yearly" and today_month_day == y_date:
                should_trigger = True

            if should_trigger:
                try:
                    logger.info(f"Triggering {freq} ETL for user {user_id} at {now_hm}")
                    run_user_etl_pipeline(user_id)
                except Exception as e:
                    logger.error(f"Scheduled ETL fail for {user_id}: {e}")
                # Always also push schema-discovered analyses into the KPI feed
                # so any auto-classified table contributes to the dashboard.
                try:
                    from ..routers.introspect import run_introspect_sync
                    res = run_introspect_sync(user_id, supabase, refresh=True)
                    logger.info(
                        f"Discovered-analyses sync for {user_id}: "
                        f"synced={res.get('synced')} failed={res.get('failed')}"
                    )
                except Exception as e:
                    logger.warning(f"Discovered-analyses sync fail for {user_id}: {e}")

    # 2. Department-level heartbeat: trigger ETL for all users in departments whose schedule matches
    try:
        dept_resp = (
            supabase.table("departments")
            .select("id, name, heartbeat_schedule, heartbeat_time")
            .eq("heartbeat_time", now_hm)
            .execute()
        )
        if hasattr(dept_resp, "data") and dept_resp.data:
            for dept in dept_resp.data:
                dept_freq = dept.get("heartbeat_schedule", "daily").lower()
                should_trigger_dept = False

                if dept_freq == "daily":
                    should_trigger_dept = True
                elif dept_freq == "weekly" and is_monday:
                    should_trigger_dept = True
                elif dept_freq == "monthly" and is_first_of_month:
                    should_trigger_dept = True

                if should_trigger_dept:
                    # Trigger ETL for all users in this department
                    users_resp = (
                        supabase.table("user_roles")
                        .select("user_id")
                        .eq("department_id", dept["id"])
                        .execute()
                    )
                    if hasattr(users_resp, "data") and users_resp.data:
                        for user_role in users_resp.data:
                            uid = user_role["user_id"]
                            try:
                                logger.info(
                                    f"Dept heartbeat: triggering {dept_freq} ETL for user {uid} in {dept['name']}"
                                )
                                run_user_etl_pipeline(uid)
                            except Exception as e:
                                logger.error(f"Dept heartbeat ETL fail for {uid}: {e}")
    except Exception as e:
        logger.error(f"Department heartbeat check failed: {e}")


def start_scheduler():
    """
    Start the APScheduler instance.
    """
    # Check every minute
    scheduler.add_job(
        process_scheduled_etl,
        "interval",
        minutes=1,
        id="scheduled_etl_check",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("APScheduler started (1-minute heartbeat for governed mesh syncs).")


def shutdown_scheduler():
    """
    Gracefully shut down the scheduler.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped.")
