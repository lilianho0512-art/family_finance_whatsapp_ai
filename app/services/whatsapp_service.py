"""WhatsApp provider facade.

Switches between Meta Cloud API and Green API based on WHATSAPP_PROVIDER env.
Public functions: send_text, get_media_url, download_media.
"""
import time
import requests
from app.config import settings
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Meta Cloud API
# ---------------------------------------------------------------------------

def _meta_api_url(path: str) -> str:
    return f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}{path}"


def _meta_headers():
    return {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }


def _meta_send_text(to_number: str, body: str, retries: int = 3) -> bool:
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("Meta WhatsApp credentials missing; skipping send_text")
        return False
    url = _meta_api_url(f"/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages")
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"preview_url": False, "body": body[:4000]},
    }
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, json=payload, headers=_meta_headers(), timeout=15)
            if resp.status_code == 200:
                return True
            last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
            logger.warning(f"meta send_text attempt {attempt} failed: {last_err}")
        except Exception as e:
            last_err = str(e)
            logger.warning(f"meta send_text attempt {attempt} exception: {e}")
        time.sleep(min(2 ** attempt, 8))
    logger.error(f"meta send_text exhausted retries to {to_number}: {last_err}")
    return False


def _meta_get_media_url(media_id: str) -> str:
    if not settings.WHATSAPP_TOKEN or not media_id:
        return ""
    try:
        resp = requests.get(
            _meta_api_url(f"/{media_id}"),
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get("url", "")
        logger.warning(f"meta get_media_url HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"meta get_media_url failed: {e}")
    return ""


def _meta_download_media(media_id: str) -> str:
    url = _meta_get_media_url(media_id)
    if not url:
        return ""
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning(f"meta download_media HTTP {resp.status_code}")
            return ""
        return _save_bytes(resp.content, resp.headers.get("Content-Type") or "", media_id)
    except Exception as e:
        logger.warning(f"meta download_media failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Green API (https://green-api.com)
# ---------------------------------------------------------------------------

def _greenapi_url(path: str) -> str:
    return (
        f"{settings.GREENAPI_BASE_URL}/waInstance{settings.GREENAPI_INSTANCE_ID}"
        f"{path}/{settings.GREENAPI_TOKEN}"
    )


def _to_chat_id(number: str) -> str:
    n = (number or "").strip().lstrip("+").replace(" ", "").replace("-", "")
    if "@" in n:
        return n
    return f"{n}@c.us"


def _greenapi_send_text(to_number: str, body: str, retries: int = 3) -> bool:
    if not settings.GREENAPI_INSTANCE_ID or not settings.GREENAPI_TOKEN:
        logger.warning("Green API credentials missing; skipping send_text")
        return False
    url = _greenapi_url("/sendMessage")
    payload = {"chatId": _to_chat_id(to_number), "message": body[:4000]}
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                return True
            last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
            logger.warning(f"greenapi send_text attempt {attempt} failed: {last_err}")
        except Exception as e:
            last_err = str(e)
            logger.warning(f"greenapi send_text attempt {attempt} exception: {e}")
        time.sleep(min(2 ** attempt, 8))
    logger.error(f"greenapi send_text exhausted retries to {to_number}: {last_err}")
    return False


def _direct_download(url: str, hint_name: str = "") -> str:
    """Green API webhook hands us a direct downloadUrl, no auth needed."""
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"direct_download HTTP {resp.status_code}")
            return ""
        return _save_bytes(resp.content, resp.headers.get("Content-Type") or "",
                           hint_name or f"download_{int(time.time())}")
    except Exception as e:
        logger.warning(f"direct_download failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Telegram Bot API
# ---------------------------------------------------------------------------

def _telegram_url(method: str) -> str:
    return f"{settings.TELEGRAM_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"


def _telegram_send_text(chat_id: str, body: str, retries: int = 3) -> bool:
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token missing; skipping send_text")
        return False
    payload = {"chat_id": chat_id, "text": body[:4000], "disable_web_page_preview": True}
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(_telegram_url("sendMessage"), json=payload, timeout=15)
            if resp.status_code == 200 and resp.json().get("ok"):
                return True
            last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
            logger.warning(f"telegram send_text attempt {attempt} failed: {last_err}")
        except Exception as e:
            last_err = str(e)
            logger.warning(f"telegram send_text attempt {attempt} exception: {e}")
        time.sleep(min(2 ** attempt, 8))
    logger.error(f"telegram send_text exhausted retries to {chat_id}: {last_err}")
    return False


def telegram_resolve_file_url(file_id: str) -> str:
    """getFile → file_path → public download URL (with token)."""
    if not settings.TELEGRAM_BOT_TOKEN or not file_id:
        return ""
    try:
        resp = requests.get(_telegram_url("getFile"), params={"file_id": file_id}, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"telegram getFile HTTP {resp.status_code}")
            return ""
        data = resp.json()
        if not data.get("ok"):
            logger.warning(f"telegram getFile not ok: {data}")
            return ""
        path = data["result"]["file_path"]
        return f"{settings.TELEGRAM_API_BASE}/file/bot{settings.TELEGRAM_BOT_TOKEN}/{path}"
    except Exception as e:
        logger.warning(f"telegram getFile failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

def _save_bytes(data: bytes, content_type: str, name_stem: str) -> str:
    ct = (content_type or "").lower()
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
    out = settings.UPLOADS_DIR / f"{name_stem}{ext}"
    out.write_bytes(data)
    return str(out)


# ---------------------------------------------------------------------------
# Public dispatch — these names are what the rest of the app calls.
# ---------------------------------------------------------------------------

def send_text(to_number: str, body: str, retries: int = 3) -> bool:
    provider = settings.WHATSAPP_PROVIDER
    if provider == "greenapi":
        return _greenapi_send_text(to_number, body, retries)
    if provider == "telegram":
        return _telegram_send_text(to_number, body, retries)
    return _meta_send_text(to_number, body, retries)


def get_media_url(media_id: str) -> str:
    if settings.WHATSAPP_PROVIDER == "greenapi":
        return media_id if media_id.startswith("http") else ""
    if settings.WHATSAPP_PROVIDER == "telegram":
        return media_id if media_id.startswith("http") else telegram_resolve_file_url(media_id)
    return _meta_get_media_url(media_id)


def download_media(media_id_or_url: str) -> str:
    """Downloads to uploads/. Accepts:
       - Meta media_id (resolves via Graph API)
       - Direct URL (Green API hands us downloadUrl)
       - Telegram file_id (resolves via getFile then downloads)
    """
    if not media_id_or_url:
        return ""
    if media_id_or_url.startswith("http"):
        return _direct_download(media_id_or_url)
    if settings.WHATSAPP_PROVIDER == "telegram":
        url = telegram_resolve_file_url(media_id_or_url)
        return _direct_download(url) if url else ""
    return _meta_download_media(media_id_or_url)
