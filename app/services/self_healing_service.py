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
    provider = settings.WHATSAPP_PROVIDER
    if provider == "meta":
        if not settings.WHATSAPP_TOKEN:
            issues.append("WHATSAPP_TOKEN missing — outbound WhatsApp messages will be skipped")
        if not settings.WHATSAPP_PHONE_NUMBER_ID:
            issues.append("WHATSAPP_PHONE_NUMBER_ID missing")
        if not settings.WHATSAPP_VERIFY_TOKEN:
            issues.append("WHATSAPP_VERIFY_TOKEN missing")
    elif provider == "greenapi":
        if not settings.GREENAPI_INSTANCE_ID:
            issues.append("GREENAPI_INSTANCE_ID missing")
        if not settings.GREENAPI_TOKEN:
            issues.append("GREENAPI_TOKEN missing")
    elif provider == "telegram":
        if not settings.TELEGRAM_BOT_TOKEN:
            issues.append("TELEGRAM_BOT_TOKEN missing")
    else:
        issues.append(
            f"Unknown WHATSAPP_PROVIDER: {provider!r} "
            "(expected 'meta', 'greenapi', or 'telegram')"
        )
    return {
        "ok": len(issues) == 0,
        "provider": provider,
        "issues": issues,
        "data_dir": str(settings.DATA_DIR),
        "uploads_dir": str(settings.UPLOADS_DIR),
        "output_dir": str(settings.OUTPUT_DIR),
        "logs_dir": str(settings.LOGS_DIR),
    }
