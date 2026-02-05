"""
Scheduler Service
Handles scheduled jobs like day-end reports at 6 PM IST
"""
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Global scheduler instance
scheduler = None


def get_scheduler():
    """Get the global scheduler instance"""
    global scheduler
    return scheduler


async def run_day_end_reports():
    """
    Job function to send day-end revenue reports
    Runs at 6 PM IST daily
    """
    from services.day_end_reports import send_day_end_reports
    from database import db
    
    print(f"[{datetime.now(IST)}] Starting day-end revenue reports job...")
    
    try:
        result = await send_day_end_reports()
        print(f"[{datetime.now(IST)}] Day-end reports completed: {result}")
        
        # Log job execution
        await db.scheduled_job_runs.insert_one({
            "job_name": "day_end_reports",
            "status": "success",
            "result": result,
            "executed_at": datetime.now(IST).isoformat(),
            "executed_at_utc": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"[{datetime.now(IST)}] Day-end reports failed: {e}")
        
        # Log job failure
        try:
            await db.scheduled_job_runs.insert_one({
                "job_name": "day_end_reports",
                "status": "failed",
                "error": str(e),
                "executed_at": datetime.now(IST).isoformat(),
                "executed_at_utc": datetime.utcnow().isoformat()
            })
        except:
            pass


async def run_whatsapp_automations():
    """
    Job function to run WhatsApp automation tasks
    Runs at 10 AM IST daily
    """
    from services.whatsapp_automation import run_scheduled_automations
    from database import db
    
    print(f"[{datetime.now(IST)}] Starting WhatsApp automations job...")
    
    try:
        result = await run_scheduled_automations()
        print(f"[{datetime.now(IST)}] WhatsApp automations completed: {result}")
        
        # Log job execution
        await db.scheduled_job_runs.insert_one({
            "job_name": "whatsapp_automations",
            "status": "success",
            "result": result,
            "executed_at": datetime.now(IST).isoformat(),
            "executed_at_utc": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"[{datetime.now(IST)}] WhatsApp automations failed: {e}")
        
        # Log job failure
        try:
            await db.scheduled_job_runs.insert_one({
                "job_name": "whatsapp_automations",
                "status": "failed",
                "error": str(e),
                "executed_at": datetime.now(IST).isoformat(),
                "executed_at_utc": datetime.utcnow().isoformat()
            })
        except:
            pass


def init_scheduler():
    """Initialize and start the scheduler"""
    global scheduler
    
    if scheduler is not None:
        print("Scheduler already initialized")
        return scheduler
    
    # Create scheduler with IST timezone
    scheduler = AsyncIOScheduler(timezone=IST)
    
    # Schedule day-end reports at 6 PM IST (18:00)
    scheduler.add_job(
        run_day_end_reports,
        trigger=CronTrigger(hour=18, minute=0, timezone=IST),
        id='day_end_reports',
        name='Day-End Revenue Reports',
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period if missed
    )
    
    # Schedule WhatsApp automations at 10 AM IST daily
    scheduler.add_job(
        run_whatsapp_automations,
        trigger=CronTrigger(hour=10, minute=0, timezone=IST),
        id='whatsapp_automations',
        name='WhatsApp Automation Tasks',
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period if missed
    )
    
    # Start the scheduler
    scheduler.start()
    
    print(f"[{datetime.now(IST)}] Scheduler started with IST timezone")
    print(f"Day-end reports scheduled for 6:00 PM IST daily")
    print(f"WhatsApp automations scheduled for 10:00 AM IST daily")
    
    # Print next run times
    for job in scheduler.get_jobs():
        print(f"Job '{job.name}' next run: {job.next_run_time}")
    
    return scheduler


def shutdown_scheduler():
    """Shutdown the scheduler gracefully"""
    global scheduler
    
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
        print("Scheduler shutdown complete")


def get_scheduled_jobs():
    """Get list of all scheduled jobs with their next run times"""
    global scheduler
    
    if not scheduler:
        return []
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return jobs


def trigger_job_now(job_id: str):
    """Manually trigger a scheduled job immediately"""
    global scheduler
    
    if not scheduler:
        return {"error": "Scheduler not initialized"}
    
    job = scheduler.get_job(job_id)
    if not job:
        return {"error": f"Job '{job_id}' not found"}
    
    # Run the job immediately
    scheduler.modify_job(job_id, next_run_time=datetime.now(IST))
    
    return {"message": f"Job '{job_id}' triggered for immediate execution"}
