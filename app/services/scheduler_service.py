from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings
from app.database import SessionLocal
from app.models import Family
from app.services import excel_export, report_service, reminder_service
from app.utils.logger import logger

_scheduler = None


def _daily_job():
    db = SessionLocal()
    try:
        families = db.query(Family).all()
        if not families:
            logger.info(f"[daily_job] (no family scope) {report_service.daily_summary_text(db, None)}")
            return
        for fam in families:
            text = report_service.daily_summary_text(db, fam.id)
            logger.info(f"[daily_job] family={fam.id} ({fam.name}) {text}")
    except Exception as e:
        logger.error(f"daily_job failed: {e}")
    finally:
        db.close()


def _monthly_job():
    db = SessionLocal()
    try:
        families = db.query(Family).all()
        if not families:
            path = excel_export.export_monthly(db, None)
            logger.info(f"[monthly_job] exported {path}")
            return
        for fam in families:
            path = excel_export.export_monthly(db, fam.id)
            logger.info(f"[monthly_job] family={fam.id} ({fam.name}) exported {path}")
    except Exception as e:
        logger.error(f"monthly_job failed: {e}")
    finally:
        db.close()


def _reminders_job():
    try:
        reminder_service.run_daily_reminders()
    except Exception as e:
        logger.error(f"reminders_job failed: {e}")


def start():
    global _scheduler
    if _scheduler is not None:
        return
    try:
        _scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)
        _scheduler.add_job(_daily_job, "cron", hour=22, minute=0, id="daily_summary")
        _scheduler.add_job(_monthly_job, "cron", day=1, hour=1, minute=0, id="monthly_export")
        _scheduler.add_job(_reminders_job, "cron", hour=9, minute=0, id="payment_reminders")
        _scheduler.start()
        logger.info("Scheduler started (daily 22:00, monthly day-1 01:00, reminders 09:00)")
    except Exception as e:
        logger.error(f"Scheduler failed to start: {e}")
        _scheduler = None


def shutdown():
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception as e:
            logger.warning(f"Scheduler shutdown error: {e}")
        _scheduler = None
