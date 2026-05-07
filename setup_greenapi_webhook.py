"""Register your public webhook URL with Green API.

Usage:
    python setup_greenapi_webhook.py https://your-ngrok.ngrok-free.app

This sets:
  - webhookUrl = <your-url>/webhook/greenapi
  - incomingWebhook = yes
  - outgoingMessageWebhook = no (we don't need echo)

Reads GREENAPI_INSTANCE_ID and GREENAPI_TOKEN from .env.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402
from app.config import settings  # noqa: E402


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    if not settings.GREENAPI_INSTANCE_ID or not settings.GREENAPI_TOKEN:
        print("ERROR: GREENAPI_INSTANCE_ID / GREENAPI_TOKEN missing in .env")
        sys.exit(1)

    public_url = sys.argv[1].rstrip("/")
    webhook_url = f"{public_url}/webhook/greenapi"

    api = (
        f"{settings.GREENAPI_BASE_URL}/waInstance{settings.GREENAPI_INSTANCE_ID}"
        f"/setSettings/{settings.GREENAPI_TOKEN}"
    )
    payload = {
        "webhookUrl": webhook_url,
        "incomingWebhook": "yes",
        "outgoingMessageWebhook": "no",
        "outgoingAPIMessageWebhook": "no",
        "stateWebhook": "yes",
        "deviceWebhook": "no",
    }
    print(f"Setting webhookUrl = {webhook_url}")
    resp = requests.post(api, json=payload, timeout=20)
    if resp.status_code == 200:
        print("OK:", resp.json())
        print("\nNext: send a WhatsApp message to your Green API instance number.")
        print("It should arrive at the webhook within 1–2 seconds.")
    else:
        print(f"FAILED HTTP {resp.status_code}: {resp.text[:500]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
