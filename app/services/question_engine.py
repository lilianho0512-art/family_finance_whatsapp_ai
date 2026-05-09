from typing import Optional, Tuple

RECORD_TYPE_QUESTION = (
    "Pick a record type:\n"
    "A. Family expense\n"
    "B. Family savings\n"
    "C. Family income\n"
    "D. Transfer\n"
    "E. Other"
)
RECORD_TYPE_OPTIONS = {
    "A": "expense",
    "B": "savings",
    "C": "income",
    "D": "transfer",
    "E": "unknown",
}

CATEGORY_QUESTION = (
    "Pick an expense category:\n"
    "A. Groceries\n"
    "B. Food\n"
    "C. Baby\n"
    "D. Utilities\n"
    "E. Petrol\n"
    "F. Medical\n"
    "G. Education\n"
    "H. Online Shopping\n"
    "I. Others"
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
    "Pick a payment method:\n"
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

ACCOUNT_QUESTION_EXPENSE = "Pick an account (which bank/wallet this expense came out of):\n" + _ACCOUNT_LIST_TEXT
ACCOUNT_QUESTION_INCOME = "Pick an account (which bank received this income):\n" + _ACCOUNT_LIST_TEXT
ACCOUNT_QUESTION_SAVINGS = "Pick a savings account (which bank this savings goes into):\n" + _ACCOUNT_LIST_TEXT

# Backward-compatible aliases (older code still referenced these names)
SAVINGS_SOURCE_QUESTION = ACCOUNT_QUESTION_SAVINGS
SAVINGS_SOURCE_OPTIONS = ACCOUNT_OPTIONS

INCOME_SOURCE_QUESTION = (
    "Pick an income source:\n"
    "A. Salary\n"
    "B. Bonus\n"
    "C. Freelance\n"
    "D. Business\n"
    "E. Investment\n"
    "F. Gift\n"
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
