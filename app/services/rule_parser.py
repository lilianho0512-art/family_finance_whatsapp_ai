import re
from app.utils.date_tools import parse_date
from app.utils.money_tools import extract_amount

# Explicit type markers — highest priority. If user (or our own confirmation
# message echoed back) writes 家庭开销/家庭储蓄/家庭收入/家庭转账 we lock that in.
EXPLICIT_TYPE_PREFIXES = [
    ("expense",  ["家庭开销", "家用开销"]),
    ("savings",  ["家庭储蓄", "家用储蓄"]),
    ("income",   ["家庭收入", "家用收入"]),
    ("transfer", ["家庭转账", "家用转账"]),
]

EXPENSE_KEYWORDS = [
    "买菜", "菜市", "超市", "买", "花了", "花掉", "外食", "开销",
    "lunch", "dinner", "breakfast", "groceries", "petrol", "fuel", "shopping",
]
SAVINGS_KEYWORDS = ["存钱", "储蓄", "save", "savings", "deposit"]
INCOME_KEYWORDS = ["工资", "薪水", "薪资", "奖金", "salary", "bonus", "income", "收入", "freelance"]
# Note: bare "transfer" intentionally NOT listed — it's a payment method too
# (Bank Transfer / Online Transfer). Standalone 'transfer' is matched via regex below.
TRANSFER_KEYWORDS = ["转账", "汇款", "duitnow"]
TRANSFER_STANDALONE_RE = re.compile(
    r"(?<!bank\s)(?<!wire\s)(?<!online\s)(?<!money\s)\btransfer\b",
    re.IGNORECASE,
)

CATEGORY_HINTS = {
    "Groceries": ["groceries", "买菜", "tesco", "aeon", "lotus", "mydin", "giant", "village grocer", "jaya grocer", "ben's", "日用品"],
    "Food": ["food", "lunch", "dinner", "breakfast", "外食", "mamak", "restaurant", "kfc", "mcdonald", "starbucks", "kopitiam", "饭", "吃"],
    "Baby": ["baby", "diaper", "尿布", "奶粉", "milk powder", "stroller", "小孩"],
    "Utilities": ["utilities", "tnb", "syabas", "indah water", "unifi", "maxis", "celcom", "digi", "water bill", "electric", "水费", "电费", "网费"],
    "Petrol": ["petrol", "petron", "shell", "petronas", "caltex", "bhpetrol", "fuel", "油费"],
    "Medical": ["medical", "clinic", "hospital", "pharmacy", "guardian", "watson", "诊所", "医院", "药"],
    "Education": ["education", "tuition", "school", "学费", "tadika", "kindergarten", "课"],
    "Online Shopping": ["online shopping", "shopee", "lazada", "amazon", "tiktok shop", "网购"],
    "Others": ["others", "其他"],
}

PAYMENT_HINTS = {
    "Touch n Go": ["tng", "touch n go", "touch'n go", "tngo"],
    "Credit Card": ["credit card", "cc", "信用卡"],
    "Debit Card": ["debit card", "debit", "借记卡"],
    "DuitNow": ["duitnow"],
    "Bank Transfer": ["transfer", "fpx", "online banking", "ibanking", "网上银行"],
    "Cash": ["cash", "现金"],
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
    # 1. Explicit "家庭X" type markers — highest priority, can't be overridden
    for rtype, hints in EXPLICIT_TYPE_PREFIXES:
        for h in hints:
            if h in text:
                return rtype
    t = text.lower()
    for kw in SAVINGS_KEYWORDS:
        if kw.lower() in t:
            return "savings"
    for kw in INCOME_KEYWORDS:
        if kw.lower() in t:
            return "income"
    # 2. TRANSFER — only via 转账/汇款/duitnow OR a standalone "transfer" word
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
    if "工资" in t or "薪水" in t or "薪资" in t or "salary" in t:
        return "Salary"
    if "奖金" in t or "bonus" in t:
        return "Bonus"
    if "freelance" in t or "兼职" in t:
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
