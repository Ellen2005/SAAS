import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from ..services.etl_service import run_user_etl_pipeline

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()

from ..core.supabase_client import get_supabase

def nightly_etl_job():
    """
    Job that runs every night. 
    It iterates over all active users who have registered a database connection.
    """
    logger.info("Executing Nightly System-Wide ETL Job...")
    
    supabase = get_supabase()
    response = supabase.table("database_connections").select("user_id").execute()
    
    if hasattr(response, 'data') and response.data:
        users = [row['user_id'] for row in response.data]
        logger.info(f"Found {len(users)} users with active database connections.")
        
        for user_id in users:
            try:
                run_user_etl_pipeline(user_id)
            except Exception as e:
                logger.error(f"Failed ETL for user {user_id}: {str(e)}")
    else:
        logger.warning("No active database connections found in Supabase.")

def start_scheduler():
    """
    Start the APScheduler instance with the registered cron jobs.
    """
    # Run every morning at 2:00 AM
    trigger = CronTrigger(hour=2, minute=0)
    scheduler.add_job(nightly_etl_job, trigger=trigger, id="nightly_etl", replace_existing=True)
    
    scheduler.start()
    logger.info("APScheduler background scheduler started.")

def shutdown_scheduler():
    """
    Gracefully shut down the scheduler.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped.")
