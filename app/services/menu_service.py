GREETING_KEYWORDS = {
    "hi", "hello", "menu", "start", "hey", "begin", "help",
}

WELCOME_TEXT = (
    "Hi, I'm your family finance AI assistant 👋\n\n"
    "I can record:\n"
    "A. Family expense\n"
    "B. Family savings\n"
    "C. Family income\n"
    "D. This month's summary\n"
    "E. Today's expenses\n"
    "F. Savings rate\n"
    "G. Export monthly report\n"
    "H. Upload receipt / screenshot / PDF\n\n"
    "Try sending me things like:\n\n"
    "1. Today Tesco RM88\n"
    "2. Today saved RM500\n"
    "3. Salary RM3800\n"
    "4. How much did I spend this month?\n"
    "5. How much did I save this month?\n"
    "6. How much on Baby category?\n"
    "7. Upload a receipt photo\n"
    "8. Undo / delete #5 (deletes the most recent or a specific ID)\n"
    "9. Balance (current computed balance per account)\n"
    "10. Set Maybank 5000 (logs today's Maybank balance snapshot)\n"
    "11. Add account OCBC (register a new account)\n\n"
    "Reply with A/B/C/D, or just send your transaction details."
)


def is_greeting(text: str) -> bool:
    if not text:
        return False
    # Strip leading "/" so Telegram-style commands like "/start" / "/menu" / "/hi" match.
    return text.strip().lower().lstrip("/") in GREETING_KEYWORDS


def get_welcome_text() -> str:
    return WELCOME_TEXT
