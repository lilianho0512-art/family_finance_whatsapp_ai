from typing import Optional
from sqlalchemy.orm import Session
from app.services import record_service
from app.utils.money_tools import format_money


def monthly_summary_text(db: Session, family_id: Optional[int]) -> str:
    inc = record_service.month_total(db, family_id, "income")
    exp = record_service.month_total(db, family_id, "expense")
    sav = record_service.month_total(db, family_id, "savings")
    rate = record_service.savings_rate(db, family_id)
    return (
        "📊 This month's summary\n"
        f"Income: {format_money(inc)}\n"
        f"Expenses: {format_money(exp)}\n"
        f"Savings: {format_money(sav)}\n"
        f"Savings rate: {rate}%"
    )


def daily_summary_text(db: Session, family_id: Optional[int]) -> str:
    return f"📅 Today's expenses: {format_money(record_service.today_expense(db, family_id))}"
