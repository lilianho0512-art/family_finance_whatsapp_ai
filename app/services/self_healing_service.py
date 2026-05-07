from app.config import settings
from app.utils.logger import logger


def ensure_folders():
    for d in [settings.DATA_DIR, settings.UPLOADS_DIR, settings.OUTPUT_DIR, settings.LOGS_DIR]:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to ensure folder {d}: {e}")


def health_summary() -> dict:
    issues = []
    if not settings.WHATSAPP_TOKEN:
        issues.append("WHATSAPP_TOKEN missing — outbound WhatsApp messages will be skipped")
    if not settings.WHATSAPP_PHONE_NUMBER_ID:
        issues.append("WHATSAPP_PHONE_NUMBER_ID missing")
    if not settings.WHATSAPP_VERIFY_TOKEN:
        issues.append("WHATSAPP_VERIFY_TOKEN missing")
    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "data_dir": str(settings.DATA_DIR),
        "uploads_dir": str(settings.UPLOADS_DIR),
        "output_dir": str(settings.OUTPUT_DIR),
        "logs_dir": str(settings.LOGS_DIR),
    }
