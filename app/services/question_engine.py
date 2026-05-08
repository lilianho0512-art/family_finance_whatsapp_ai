from typing import Optional, Tuple

RECORD_TYPE_QUESTION = (
    "请选择这笔记录类型：\n"
    "A. 家庭开销\n"
    "B. 家庭储蓄\n"
    "C. 家庭收入\n"
    "D. 转账\n"
    "E. 其他"
)
RECORD_TYPE_OPTIONS = {
    "A": "expense",
    "B": "savings",
    "C": "income",
    "D": "transfer",
    "E": "unknown",
}

CATEGORY_QUESTION = (
    "请选择开销分类：\n"
    "A. Groceries 买菜/日用品\n"
    "B. Food 外食\n"
    "C. Baby 小孩用品\n"
    "D. Utilities 水电网\n"
    "E. Petrol 油费\n"
    "F. Medical 医疗\n"
    "G. Education 教育\n"
    "H. Online Shopping 网购\n"
    "I. Others 其他"
)
CATEGORY_OPTIONS = {
    "A": "Groceries",
    "B": "Food",
    "C": "Baby",
    "D": "Utilities",
    "E": "Petrol",
    "F": "Medical",
    "G": "Education",
    "H": "Online Shopping",
    "I": "Others",
}

PAYMENT_QUESTION = (
    "请选择付款方式：\n"
    "A. Cash\n"
    "B. Credit Card\n"
    "C. Debit Card\n"
    "D. Touch n Go\n"
    "E. Bank Transfer\n"
    "F. DuitNow\n"
    "G. Other"
)
PAYMENT_OPTIONS = {
    "A": "Cash",
    "B": "Credit Card",
    "C": "Debit Card",
    "D": "Touch n Go",
    "E": "Bank Transfer",
    "F": "DuitNow",
    "G": "Other",
}

ACCOUNT_OPTIONS = {
    "A": "Maybank",
    "B": "CIMB",
    "C": "Public Bank",
    "D": "Hong Leong",
    "E": "UOB",
    "F": "ASB",
    "G": "Tabung Haji",
    "H": "EPF",
    "I": "Cash",
    "J": "Other",
}

_ACCOUNT_LIST_TEXT = (
    "A. Maybank\n"
    "B. CIMB\n"
    "C. Public Bank\n"
    "D. Hong Leong\n"
    "E. UOB\n"
    "F. ASB\n"
    "G. Tabung Haji\n"
    "H. EPF\n"
    "I. Cash\n"
    "J. Other"
)

ACCOUNT_QUESTION_EXPENSE = "请选择账户（这笔开销从哪个银行/钱包扣）：\n" + _ACCOUNT_LIST_TEXT
ACCOUNT_QUESTION_INCOME = "请选择账户（这笔收入进哪个银行）：\n" + _ACCOUNT_LIST_TEXT
ACCOUNT_QUESTION_SAVINGS = "请选择储蓄账户（这笔储蓄存到哪个银行）：\n" + _ACCOUNT_LIST_TEXT

# Backward-compatible aliases (older code still referenced these names)
SAVINGS_SOURCE_QUESTION = ACCOUNT_QUESTION_SAVINGS
SAVINGS_SOURCE_OPTIONS = ACCOUNT_OPTIONS

INCOME_SOURCE_QUESTION = (
    "请选择收入来源：\n"
    "A. Salary 工资\n"
    "B. Bonus 奖金\n"
    "C. Freelance 兼职\n"
    "D. Business 生意\n"
    "E. Investment 投资\n"
    "F. Gift 礼金\n"
    "G. Other"
)
INCOME_SOURCE_OPTIONS = {
    "A": "Salary",
    "B": "Bonus",
    "C": "Freelance",
    "D": "Business",
    "E": "Investment",
    "F": "Gift",
    "G": "Other",
}


def determine_next_question(record) -> Optional[Tuple[str, str, dict]]:
    """Return (step, question, options) or None when record is complete."""
    rt = (record.record_type or "unknown").lower()
    acc = getattr(record, "account", None)
    if rt == "unknown" or not rt:
        return ("ask_record_type", RECORD_TYPE_QUESTION, RECORD_TYPE_OPTIONS)
    if rt == "expense":
        if not record.category:
            return ("ask_category", CATEGORY_QUESTION, CATEGORY_OPTIONS)
        if not record.payment_method:
            return ("ask_payment_method", PAYMENT_QUESTION, PAYMENT_OPTIONS)
        if not acc:
            return ("ask_account_expense", ACCOUNT_QUESTION_EXPENSE, ACCOUNT_OPTIONS)
    if rt == "savings":
        if not acc:
            return ("ask_account_savings", ACCOUNT_QUESTION_SAVINGS, ACCOUNT_OPTIONS)
    if rt == "income":
        if not record.source:
            return ("ask_income_source", INCOME_SOURCE_QUESTION, INCOME_SOURCE_OPTIONS)
        if not acc:
            return ("ask_account_income", ACCOUNT_QUESTION_INCOME, ACCOUNT_OPTIONS)
    if rt == "transfer":
        if not record.payment_method:
            return ("ask_payment_method", PAYMENT_QUESTION, PAYMENT_OPTIONS)
        if not acc:
            return ("ask_account_expense", ACCOUNT_QUESTION_EXPENSE, ACCOUNT_OPTIONS)
    return None


def resolve_answer(step: str, answer: str):
    if not answer:
        return None
    key = answer.strip().upper()[:1]
    mapping = {
        "ask_record_type": RECORD_TYPE_OPTIONS,
        "ask_category": CATEGORY_OPTIONS,
        "ask_payment_method": PAYMENT_OPTIONS,
        "ask_savings_source": ACCOUNT_OPTIONS,  # legacy alias
        "ask_income_source": INCOME_SOURCE_OPTIONS,
        "ask_account_expense": ACCOUNT_OPTIONS,
        "ask_account_savings": ACCOUNT_OPTIONS,
        "ask_account_income": ACCOUNT_OPTIONS,
    }
    table = mapping.get(step)
    if not table:
        return None
    return table.get(key)
