import re

AMOUNT_STRICT_RE = re.compile(r"(?:RM|MYR|\$)\s*([0-9]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)
NUMBER_RE = re.compile(r"([0-9]+(?:\.[0-9]{1,2})?)")


def extract_amount(text: str):
    if not text:
        return None
    m = AMOUNT_STRICT_RE.search(text)
    if m:
        try:
            return round(float(m.group(1)), 2)
        except Exception:
            pass
    nums = NUMBER_RE.findall(text)
    if not nums:
        return None
    try:
        vals = [float(n) for n in nums if n]
        if not vals:
            return None
        return round(max(vals), 2)
    except Exception:
        return None


def format_money(amount, currency: str = "MYR") -> str:
    try:
        return f"{currency} {float(amount):.2f}"
    except Exception:
        return f"{currency} {amount}"
