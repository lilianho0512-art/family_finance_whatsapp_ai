"""Currency support: a fixed list of major ASEAN/G7 currencies.

We intentionally do NOT do FX conversion — every record is kept in its
native currency. Reports group totals per currency.
"""
import re
from typing import Optional, Tuple

# Order matters for UI dropdowns (most-likely first).
SUPPORTED_CURRENCIES = [
    "MYR", "SGD", "USD", "EUR", "GBP", "JPY",
    "AUD", "IDR", "THB", "PHP", "HKD", "CNY",
]

# Display symbols. Currencies not listed fall back to the ISO code.
CURRENCY_SYMBOLS = {
    "MYR": "RM",
    "SGD": "S$",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "AUD": "A$",
    "IDR": "Rp",
    "THB": "฿",
    "PHP": "₱",
    "HKD": "HK$",
    "CNY": "¥",
}

DEFAULT_CURRENCY = "MYR"


def is_supported(code: str) -> bool:
    return (code or "").upper() in SUPPORTED_CURRENCIES


def normalize(code: str) -> str:
    """Return a known currency code or DEFAULT_CURRENCY."""
    c = (code or "").upper().strip()
    return c if c in SUPPORTED_CURRENCIES else DEFAULT_CURRENCY


def symbol(code: str) -> str:
    return CURRENCY_SYMBOLS.get(normalize(code), normalize(code))


def format_money(amount, currency: str = DEFAULT_CURRENCY) -> str:
    """Render an amount with its currency symbol prefix.

    Examples:
        format_money(88.5, "MYR") -> "RM 88.50"
        format_money(50, "USD")   -> "$ 50.00"
        format_money(1000, "JPY") -> "¥ 1000.00"
    """
    cur = normalize(currency)
    sym = CURRENCY_SYMBOLS.get(cur, cur)
    try:
        return f"{sym} {float(amount):.2f}"
    except (TypeError, ValueError):
        return f"{sym} {amount}"


# ---------------------------------------------------------------------------
# Hint extraction from free-text user input
# ---------------------------------------------------------------------------

# Order matters — longer/more specific symbols first so "S$" beats "$".
_SYMBOL_HINTS = [
    ("HK$", "HKD"),
    ("S$",  "SGD"),
    ("A$",  "AUD"),
    ("RM",  "MYR"),
    ("Rp",  "IDR"),
    ("£",   "GBP"),
    ("€",   "EUR"),
    ("¥",   "JPY"),  # ambiguous with CNY; we default to JPY here
    ("฿",   "THB"),
    ("₱",   "PHP"),
    ("$",   "USD"),
]

_CODE_RE = re.compile(
    r"\b(MYR|SGD|USD|EUR|GBP|JPY|AUD|IDR|THB|PHP|HKD|CNY)\b",
    re.IGNORECASE,
)


def parse_currency_hint(text: str) -> Optional[str]:
    """Look for an ISO code or known symbol in the text. Returns the ISO
    code (e.g. "USD") or None if no hint is found."""
    if not text:
        return None
    m = _CODE_RE.search(text)
    if m:
        return m.group(1).upper()
    # Symbols are case-sensitive enough that we don't lowercase here
    for sym, code in _SYMBOL_HINTS:
        if sym in text:
            return code
    return None


def split_amount_and_currency(text: str) -> Tuple[Optional[float], Optional[str]]:
    """Helper for parsers — returns (amount, currency_hint)."""
    from app.utils.money_tools import extract_amount  # avoid cycle
    return extract_amount(text), parse_currency_hint(text)
