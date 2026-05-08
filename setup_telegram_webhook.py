"""Register your public webhook URL with Telegram Bot API.

Usage:
    python setup_telegram_webhook.py https://your-tunnel.trycloudflare.com
    python setup_telegram_webhook.py --info       # show current webhook
    python setup_telegram_webhook.py --delete     # remove webhook

Reads TELEGRAM_BOT_TOKEN from .env.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402
from app.config import settings  # noqa: E402


def _api(method: str) -> str:
    return f"{settings.TELEGRAM_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    if not settings.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN missing in .env")
        sys.exit(1)

    if args[0] == "--info":
        r = requests.get(_api("getWebhookInfo"), timeout=15).json()
        print(r)
        return

    if args[0] == "--delete":
        r = requests.post(_api("deleteWebhook"), timeout=15).json()
        print("OK:", r)
        return

    public_url = args[0].rstrip("/")
    webhook_url = f"{public_url}/webhook/telegram"
    print(f"Setting webhook = {webhook_url}")
    r = requests.post(
        _api("setWebhook"),
        json={
            "url": webhook_url,
            "allowed_updates": ["message", "edited_message"],
            "drop_pending_updates": True,
        },
        timeout=20,
    )
    if r.status_code == 200 and r.json().get("ok"):
        print("OK:", r.json())
        # Confirm
        info = requests.get(_api("getWebhookInfo"), timeout=15).json()
        print("Confirmed:", info.get("result", {}).get("url"))
        print("\nNext: open Telegram → search your bot → send /start")
    else:
        print(f"FAILED HTTP {r.status_code}: {r.text[:500]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
