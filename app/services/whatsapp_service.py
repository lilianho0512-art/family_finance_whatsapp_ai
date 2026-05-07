import time
import requests
from app.config import settings
from app.utils.logger import logger


def _api_url(path: str) -> str:
    return f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}{path}"


def _headers():
    return {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }


def send_text(to_number: str, body: str, retries: int = 3) -> bool:
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials missing; skipping send_text")
        return False
    url = _api_url(f"/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages")
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"preview_url": False, "body": body[:4000]},
    }
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
            if resp.status_code == 200:
                return True
            last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
            logger.warning(f"send_text attempt {attempt} failed: {last_err}")
        except Exception as e:
            last_err = str(e)
            logger.warning(f"send_text attempt {attempt} exception: {e}")
        time.sleep(min(2 ** attempt, 8))
    logger.error(f"send_text exhausted retries to {to_number}: {last_err}")
    return False


def get_media_url(media_id: str) -> str:
    if not settings.WHATSAPP_TOKEN or not media_id:
        return ""
    try:
        resp = requests.get(
            _api_url(f"/{media_id}"),
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get("url", "")
        logger.warning(f"get_media_url HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"get_media_url failed: {e}")
    return ""


def download_media(media_id: str) -> str:
    url = get_media_url(media_id)
    if not url:
        return ""
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning(f"download_media HTTP {resp.status_code}")
            return ""
        ct = (resp.headers.get("Content-Type") or "").lower()
        if "jpeg" in ct or "jpg" in ct:
            ext = ".jpg"
        elif "png" in ct:
            ext = ".png"
        elif "pdf" in ct:
            ext = ".pdf"
        elif "webp" in ct:
            ext = ".webp"
        elif "heic" in ct:
            ext = ".heic"
        else:
            ext = ".bin"
        out = settings.UPLOADS_DIR / f"{media_id}{ext}"
        out.write_bytes(resp.content)
        return str(out)
    except Exception as e:
        logger.warning(f"download_media failed: {e}")
        return ""
