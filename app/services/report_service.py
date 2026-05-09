from typing import Optional
from sqlalchemy.orm import Session
from app.models import Family
from app.services import record_service
from app.utils import fx
from app.utils.money_tools import format_money


def _family_currency(db: Session, family_id: Optional[int]) -> str:
    if family_id is None:
        return "MYR"
    fam = db.query(Family).get(family_id)
    return (fam.default_currency if fam else None) or "MYR"


def monthly_summary_text(db: Session, family_id: Optional[int], currency: Optional[str] = None) -> str:
    cur = currency or _family_currency(db, family_id)
    inc_g = record_service.month_total_grouped(db, family_id, "income")
    exp_g = record_service.month_total_grouped(db, family_id, "expense")
    sav_g = record_service.month_total_grouped(db, family_id, "savings")
    inc = fx.convert_grouped(inc_g, cur)
    exp = fx.convert_grouped(exp_g, cur)
    sav = fx.convert_grouped(sav_g, cur)
    rate = round((sav / inc * 100), 2) if inc > 0 else 0.0
    note = ""
    if any(len(g) > 1 or (g and cur not in g) for g in (inc_g, exp_g, sav_g)):
        note = f"\n(converted to {cur} at today's FX)"
    return (
        "📊 This month's summary\n"
        f"Income: {format_money(inc, cur)}\n"
        f"Expenses: {format_money(exp, cur)}\n"
        f"Savings: {format_money(sav, cur)}\n"
        f"Savings rate: {rate}%"
        f"{note}"
    )


def daily_summary_text(db: Session, family_id: Optional[int], currency: Optional[str] = None) -> str:
    cur = currency or _family_currency(db, family_id)
    today_g = record_service.today_expense_grouped(db, family_id)
    today = fx.convert_grouped(today_g, cur)
    return f"📅 Today's expenses: {format_money(today, cur)}"
