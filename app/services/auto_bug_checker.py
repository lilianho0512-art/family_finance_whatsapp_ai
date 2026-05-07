import functools
import traceback
from app.database import SessionLocal
from app.models import BugLog
from app.utils.logger import logger


def log_bug(error_type: str, error_message: str, file_name: str = "",
            function_name: str = "", traceback_text: str = "",
            auto_fixed: bool = False, fix_note: str = ""):
    try:
        db = SessionLocal()
        try:
            bl = BugLog(
                error_type=(error_type or "")[:100],
                error_message=(error_message or "")[:2000],
                file_name=(file_name or "")[:200],
                function_name=(function_name or "")[:200],
                traceback_text=(traceback_text or "")[:6000],
                auto_fixed=1 if auto_fixed else 0,
                fix_note=(fix_note or "")[:500],
            )
            db.add(bl)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to write bug log: {e}")


def safe(default=None, file_name: str = ""):
    """Decorator that catches exceptions, logs to bug_logs, returns default."""
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                tb = traceback.format_exc()
                logger.error(f"{func.__name__} error: {e}\n{tb}")
                log_bug(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    file_name=file_name,
                    function_name=func.__name__,
                    traceback_text=tb,
                )
                return default
        return wrapper
    return deco
