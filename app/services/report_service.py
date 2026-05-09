from typing import Optional
from sqlalchemy.orm import Session
from app.models import Family
from app.services import record_service
from app.utils.money_tools import format_money


def _family_currency(db: Session, family_id: Optional[int]) -> str:
    if family_id is None:
        return "MYR"
    fam = db.query(Family).get(family_id)
    return (fam.default_currency if fam else None) or "MYR"


def monthly_summary_text(db: Session, family_id: Optional[int], currency: Optional[str] = None) -> str:
    cur = currency or _family_currency(db, family_id)
    inc = record_service.month_total(db, family_id, "income")
    exp = record_service.month_total(db, family_id, "expense")
    sav = record_service.month_total(db, family_id, "savings")
    rate = record_service.savings_rate(db, family_id)
    return (
        "📊 This month's summary\n"
        f"Income: {format_money(inc, cur)}\n"
        f"Expenses: {format_money(exp, cur)}\n"
        f"Savings: {format_money(sav, cur)}\n"
        f"Savings rate: {rate}%"
    )


def daily_summary_text(db: Session, family_id: Optional[int], currency: Optional[str] = None) -> str:
    cur = currency or _family_currency(db, family_id)
    return f"📅 Today's expenses: {format_money(record_service.today_expense(db, family_id), cur)}"
