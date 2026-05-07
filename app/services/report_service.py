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
        "📊 本月总结\n"
        f"收入：{format_money(inc)}\n"
        f"开销：{format_money(exp)}\n"
        f"储蓄：{format_money(sav)}\n"
        f"储蓄率：{rate}%"
    )


def daily_summary_text(db: Session, family_id: Optional[int]) -> str:
    return f"📅 今天开销：{format_money(record_service.today_expense(db, family_id))}"
