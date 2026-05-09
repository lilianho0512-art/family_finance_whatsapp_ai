"""FX rate fetcher with on-disk daily cache.

Reports/dashboard/Excel-summary use this to convert per-currency totals
into the family's default currency. Per-record/loan/bill rows still
display in their native currency — conversion is for aggregates only.

Source: open.er-api.com (free, no API key, ECB-backed, covers all 12
currencies the app supports). Only "latest" rates are available — we
ignore the `day` argument when fetching but still partition the cache
by date so a stale day rolls over naturally.
"""
import json
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional

import requests

from app.config import settings
from app.utils.logger import logger

_CACHE_PATH: Path = settings.DATA_DIR / "fx_cache.json"
_LOCK = threading.Lock()
# open.er-api.com always serves "latest" — we partition cache by date so a
# new day refetches automatically.
_API_LATEST = "https://open.er-api.com/v6/latest/{base}"
_TIMEOUT = 6  # seconds


def _today() -> str:
    return date.today().isoformat()


def _load_cache() -> dict:
    try:
        if _CACHE_PATH.exists():
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"fx cache load failed: {e}")
    return {}


def _save_cache(cache: dict) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"fx cache save failed: {e}")


def _fetch_rates_from_base(base: str, day: str) -> Optional[Dict[str, float]]:
    """Hit open.er-api.com once for `base` and return {code: rate}.

    `day` is used only as a cache-partition key by the caller — the API
    always returns latest rates."""
    url = _API_LATEST.format(base=base.upper())
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        if resp.status_code != 200:
            logger.warning(f"fx HTTP {resp.status_code} for {base} @ {day}: {resp.text[:200]}")
            return None
        data = resp.json()
        if data.get("result") != "success":
            logger.warning(f"fx upstream not success for {base}: {data.get('error-type', data)}")
            return None
        rates = data.get("rates")
        if not isinstance(rates, dict):
            logger.warning(f"fx response missing rates for {base} @ {day}")
            return None
        return {k.upper(): float(v) for k, v in rates.items()}
    except Exception as e:
        logger.warning(f"fx fetch error for {base} @ {day}: {e}")
        return None


def get_rate(from_cur: str, to_cur: str, day: Optional[str] = None) -> float:
    """Return how many `to_cur` you get per 1 `from_cur` on `day` (default: today).

    Same currency → 1.0. API failure → 1.0 with a warning logged.
    Cached on disk per (day, base, target).
    """
    f = (from_cur or "").upper()
    t = (to_cur or "").upper()
    if not f or not t or f == t:
        return 1.0
    day = day or _today()
    with _LOCK:
        cache = _load_cache()
        bucket = cache.setdefault(day, {}).setdefault(f, {})
        if t in bucket:
            return float(bucket[t])
        # Miss — fetch all rates for this base in one call so neighbour pairs are warm.
        rates = _fetch_rates_from_base(f, day)
        if rates is None:
            logger.warning(f"fx fallback to 1.0 for {f}->{t} @ {day}")
            return 1.0
        bucket.update(rates)
        _save_cache(cache)
        return float(bucket.get(t, 1.0))


def convert(amount: float, from_cur: str, to_cur: str, day: Optional[str] = None) -> float:
    """Convert `amount` from `from_cur` to `to_cur`, rounded to 2dp."""
    if amount is None:
        return 0.0
    rate = get_rate(from_cur, to_cur, day)
    return round(float(amount) * rate, 2)


def convert_grouped(amount_by_currency: Dict[str, float], to_cur: str, day: Optional[str] = None) -> float:
    """Sum a {currency: amount} dict converted to `to_cur`, rounded to 2dp."""
    total = 0.0
    for cur, amt in (amount_by_currency or {}).items():
        if amt:
            total += float(amt) * get_rate(cur, to_cur, day)
    return round(total, 2)


def cache_age_days() -> Optional[int]:
    """Days since the cache file was last modified (None if missing). Useful
    for showing a 'rates updated N days ago' note."""
    try:
        if not _CACHE_PATH.exists():
            return None
        mtime = datetime.fromtimestamp(_CACHE_PATH.stat().st_mtime)
        return (datetime.now() - mtime).days
    except Exception:
        return None
