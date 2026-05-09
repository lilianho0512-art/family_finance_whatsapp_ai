import re
from app.utils.date_tools import parse_date
from app.utils.money_tools import extract_amount

# Explicit type markers — highest priority. If the user (or our own confirmation
# message echoed back) says "family expense" / "family savings" / etc., we lock
# that in as the record type.
EXPLICIT_TYPE_PREFIXES = [
    ("expense",  ["family expense"]),
    ("savings",  ["family savings"]),
    ("income",   ["family income"]),
    ("transfer", ["family transfer"]),
]

EXPENSE_KEYWORDS = [
    "lunch", "dinner", "breakfast", "groceries", "petrol", "fuel", "shopping",
    "spent", "expense", "bought", "buy",
]
SAVINGS_KEYWORDS = ["save", "saved", "savings", "deposit"]
INCOME_KEYWORDS = ["salary", "bonus", "income", "freelance"]
# Note: bare "transfer" intentionally NOT listed — it's a payment method too
# (Bank Transfer / Online Transfer). Standalone 'transfer' is matched via regex below.
TRANSFER_KEYWORDS = ["duitnow", "remittance"]
TRANSFER_STANDALONE_RE = re.compile(
    r"(?<!bank\s)(?<!wire\s)(?<!online\s)(?<!money\s)\btransfer\b",
    re.IGNORECASE,
)

CATEGORY_HINTS = {
    "Groceries": ["groceries", "tesco", "aeon", "lotus", "mydin", "giant", "village grocer", "jaya grocer", "ben's"],
    "Food": ["food", "lunch", "dinner", "breakfast", "mamak", "restaurant", "kfc", "mcdonald", "starbucks", "kopitiam"],
    "Baby": ["baby", "diaper", "milk powder", "stroller"],
    "Utilities": ["utilities", "tnb", "syabas", "indah water", "unifi", "maxis", "celcom", "digi", "water bill", "electric"],
    "Petrol": ["petrol", "petron", "shell", "petronas", "caltex", "bhpetrol", "fuel"],
    "Medical": ["medical", "clinic", "hospital", "pharmacy", "guardian", "watson"],
    "Education": ["education", "tuition", "school", "tadika", "kindergarten"],
    "Online Shopping": ["online shopping", "shopee", "lazada", "amazon", "tiktok shop"],
    "Others": ["others"],
}

PAYMENT_HINTS = {
    "Touch n Go": ["tng", "touch n go", "touch'n go", "tngo"],
    "Credit Card": ["credit card", "cc"],
    "Debit Card": ["debit card", "debit"],
    "DuitNow": ["duitnow"],
    "Bank Transfer": ["transfer", "fpx", "online banking", "ibanking"],
    "Cash": ["cash"],
}

COMMON_MERCHANTS = [
    "Tesco", "Aeon", "Lotus", "Mydin", "Giant", "Shopee", "Lazada", "Petron", "Shell",
    "Petronas", "Maxis", "Celcom", "Digi", "Unifi", "TNB", "Maybank", "CIMB", "KFC",
    "McDonald", "Starbucks", "Watson", "Guardian", "Mr DIY", "Daiso", "IKEA",
    "Village Grocer", "Jaya Grocer",
]

MERCHANT_RE = re.compile(r"\b([A-Z][A-Za-z0-9&'\-]{1,30}(?:\s+[A-Z][A-Za-z0-9&'\-]{1,30})*)\b")


def detect_record_type(text: str) -> str:
    if not text:
        return "unknown"
    t = text.lower()
    # 1. Explicit "family X" type markers — highest priority, can't be overridden
    for rtype, hints in EXPLICIT_TYPE_PREFIXES:
        for h in hints:
            if h in t:
                return rtype
    for kw in SAVINGS_KEYWORDS:
        if kw.lower() in t:
            return "savings"
    for kw in INCOME_KEYWORDS:
        if kw.lower() in t:
            return "income"
    # 2. TRANSFER — only via duitnow/remittance OR a standalone "transfer" word
    #    (NOT "Bank Transfer" / "Online Transfer" — those are payment methods)
    for kw in TRANSFER_KEYWORDS:
        if kw.lower() in t:
            return "transfer"
    if TRANSFER_STANDALONE_RE.search(text):
        return "transfer"
    for kw in EXPENSE_KEYWORDS:
        if kw.lower() in t:
            return "expense"
    return "unknown"


def detect_category(text: str) -> str:
    t = (text or "").lower()
    for cat, hints in CATEGORY_HINTS.items():
        for h in hints:
            if h.lower() in t:
                return cat
    return ""


def detect_payment_method(text: str) -> str:
    t = (text or "").lower()
    for pm, hints in PAYMENT_HINTS.items():
        for h in hints:
            if h.lower() in t:
                return pm
    return ""


def detect_merchant(text: str) -> str:
    if not text:
        return ""
    tl = text.lower()
    for c in COMMON_MERCHANTS:
        if c.lower() in tl:
            return c
    # Strip out RM/MYR amounts so they don't get matched as merchant.
    cleaned = re.sub(r"(?:RM|MYR|\$)\s*[0-9]+(?:\.[0-9]{1,2})?", " ", text, flags=re.IGNORECASE)
    m = MERCHANT_RE.search(cleaned)
    if m:
        cand = m.group(1).strip()
        # Skip pseudo-merchants like "RM500", "MYR123"
        if re.match(r"^(?:RM|MYR)[0-9]", cand, flags=re.IGNORECASE):
            return ""
        return cand
    return ""


def detect_income_source(text: str) -> str:
    t = (text or "").lower()
    if "salary" in t:
        return "Salary"
    if "bonus" in t:
        return "Bonus"
    if "freelance" in t:
        return "Freelance"
    return ""


def parse(text: str) -> dict:
    text = text or ""
    rtype = detect_record_type(text)
    amount = extract_amount(text) or 0.0
    d = parse_date(text)
    merchant = detect_merchant(text) if rtype in ("expense", "unknown") else ""
    category = detect_category(text) if rtype in ("expense", "unknown") else ""
    payment = detect_payment_method(text)
    source = detect_income_source(text) if rtype == "income" else ""
    missing = []
    if rtype == "unknown":
        missing.append("record_type")
    if rtype == "expense":
        if not category:
            missing.append("category")
        if not payment:
            missing.append("payment_method")
    if rtype == "savings" and not source:
        missing.append("source")
    if rtype == "income" and not source:
        missing.append("source")
    if rtype == "transfer" and not payment:
        missing.append("payment_method")
    return {
        "record_type": rtype,
        "date": d.isoformat(),
        "merchant": merchant,
        "amount": amount,
        "currency": "MYR",
        "category": category,
        "payment_method": payment,
        "source": source,
        "note": "",
        "confidence_score": 0.5,
        "missing_fields": missing,
    }
