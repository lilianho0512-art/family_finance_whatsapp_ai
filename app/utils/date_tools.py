import re
from datetime import date, timedelta
from dateutil import parser as dateutil_parser

CN_TODAY = ["今天", "今日", "today"]
CN_YESTERDAY = ["昨天", "昨日", "yesterday"]
CN_TOMORROW = ["明天", "明日", "tomorrow"]


def parse_date(text, fallback: date = None) -> date:
    if fallback is None:
        fallback = date.today()
    if text is None:
        return fallback
    if isinstance(text, date):
        return text
    text = str(text).strip()
    if not text:
        return fallback
    low = text.lower()
    for kw in CN_TODAY:
        if kw in low:
            return date.today()
    for kw in CN_YESTERDAY:
        if kw in low:
            return date.today() - timedelta(days=1)
    for kw in CN_TOMORROW:
        if kw in low:
            return date.today() + timedelta(days=1)
    m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            pass
    try:
        return dateutil_parser.parse(text, fuzzy=True).date()
    except Exception:
        return fallback


def month_range(d: date = None):
    if d is None:
        d = date.today()
    start = d.replace(day=1)
    if start.month == 12:
        nxt = start.replace(year=start.year + 1, month=1)
    else:
        nxt = start.replace(month=start.month + 1)
    end = nxt - timedelta(days=1)
    return start, end
