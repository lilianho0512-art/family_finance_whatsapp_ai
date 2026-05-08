import requests
from app.config import settings
from app.utils.json_tools import extract_json
from app.utils.logger import logger
from app.services import rule_parser

SYSTEM_PROMPT = (
    "You are a strict JSON extractor for Malaysian family finance WhatsApp messages. "
    "Output ONLY a JSON object — no markdown, no explanation, no code fences.\n"
    "Schema:\n"
    "{\n"
    '  "record_type": "expense|savings|income|transfer|unknown",\n'
    '  "date": "YYYY-MM-DD",\n'
    '  "merchant": str,\n'
    '  "amount": float,\n'
    '  "currency": "MYR",\n'
    '  "category": str,\n'
    '  "payment_method": str,\n'
    '  "source": str,\n'
    '  "note": str,\n'
    '  "confidence_score": float,\n'
    '  "missing_fields": [str]\n'
    "}\n"
    "Use empty string \"\" for unknown text fields. Use 0 for unknown amounts."
)


def parse_with_ollama(text: str):
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\nMessage:\n{text}\n\nJSON:",
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }
    try:
        # Short timeout: WhatsApp Cloud API retries if we don't reply in ~5s,
        # so we prefer to fall back to rule_parser rather than block the webhook.
        resp = requests.post(url, json=payload, timeout=4)
        if resp.status_code != 200:
            logger.warning(f"Ollama HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        data = resp.json()
        return extract_json(data.get("response", ""))
    except Exception as e:
        logger.info(f"Ollama unavailable, falling back: {e}")
        return None


def parse_with_gemini(text: str):
    if not settings.GEMINI_API_KEY:
        return None
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    )
    payload = {
        "contents": [
            {"parts": [{"text": SYSTEM_PROMPT + "\n\nMessage:\n" + text + "\n\nJSON:"}]}
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    try:
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code != 200:
            logger.warning(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        data = resp.json()
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        return extract_json(raw)
    except Exception as e:
        logger.warning(f"Gemini call failed: {e}")
        return None


_DATE_KEYWORDS = (
    "今天", "今日", "昨天", "昨日", "明天", "明日",
    "today", "yesterday", "tomorrow",
)
_DATE_PATTERN_RE = __import__("re").compile(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\b\d{1,2}[-/]\d{1,2}\b")


def _normalize(parsed, fallback_text: str) -> dict:
    rule = rule_parser.parse(fallback_text)
    if not parsed or not isinstance(parsed, dict):
        return rule
    out = dict(rule)
    # rule_parser is high-precision on explicit keywords (存钱/工资/今天/...) and on
    # RM-prefixed amounts. Trust it over the LLM for those, otherwise let AI fill gaps.
    rule_explicit_type = (rule.get("record_type") or "unknown") != "unknown"
    rule_has_amount = float(rule.get("amount") or 0) > 0
    low = (fallback_text or "").lower()
    rule_explicit_date = any(kw in low for kw in _DATE_KEYWORDS) or bool(_DATE_PATTERN_RE.search(fallback_text or ""))
    for k, v in parsed.items():
        if v in (None, "", []):
            continue
        if k == "record_type" and rule_explicit_type:
            continue
        if k == "amount" and rule_has_amount:
            continue
        if k == "date" and rule_explicit_date:
            continue
        out[k] = v
    try:
        out["amount"] = float(out.get("amount") or 0)
    except Exception:
        out["amount"] = rule["amount"]
    if not out.get("currency"):
        out["currency"] = "MYR"
    if not out.get("date"):
        out["date"] = rule["date"]
    try:
        out["confidence_score"] = float(out.get("confidence_score") or 0.5)
    except Exception:
        out["confidence_score"] = 0.5
    rt = (out.get("record_type") or "unknown").lower()
    out["record_type"] = rt
    missing = []
    if rt == "unknown":
        missing.append("record_type")
    if rt == "expense":
        if not out.get("category"):
            missing.append("category")
        if not out.get("payment_method"):
            missing.append("payment_method")
    if rt == "savings" and not out.get("source"):
        missing.append("source")
    if rt == "income" and not out.get("source"):
        missing.append("source")
    if rt == "transfer" and not out.get("payment_method"):
        missing.append("payment_method")
    out["missing_fields"] = missing
    return out


def parse(text: str) -> dict:
    parsed = parse_with_ollama(text)
    if parsed is None:
        parsed = parse_with_gemini(text)
    return _normalize(parsed, text)
