from datetime import date
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import FinancialRecord
from app.utils.date_tools import month_range


def _scope(q, family_id: Optional[int]):
    if family_id is not None:
        q = q.filter(FinancialRecord.family_id == family_id)
    return q


def create_record(db: Session, **fields) -> FinancialRecord:
    r = FinancialRecord(**fields)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def update_record(db: Session, record_id: int, **fields):
    r = db.query(FinancialRecord).get(record_id)
    if r is None:
        return None
    for k, v in fields.items():
        if v is not None:
            setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r


def get_record(db: Session, record_id: int):
    return db.query(FinancialRecord).get(record_id)


def list_recent(db: Session, family_id: Optional[int], limit: int = 20):
    q = _scope(db.query(FinancialRecord), family_id)
    return q.order_by(FinancialRecord.created_at.desc()).limit(limit).all()


def list_all(db: Session, family_id: Optional[int], status: str = None):
    q = _scope(db.query(FinancialRecord), family_id)
    if status:
        q = q.filter(FinancialRecord.status == status)
    return q.order_by(FinancialRecord.created_at.desc()).all()


def _completed(q):
    return q.filter(FinancialRecord.status == "completed")


def sum_by_type(db: Session, family_id: Optional[int], record_type: str,
                start: date, end: date) -> float:
    q = _scope(
        db.query(func.coalesce(func.sum(FinancialRecord.amount), 0.0)),
        family_id,
    ).filter(
        FinancialRecord.record_type == record_type,
        FinancialRecord.date >= start,
        FinancialRecord.date <= end,
    )
    val = _completed(q).scalar()
    return float(val or 0)


def month_total(db: Session, family_id: Optional[int], record_type: str, ref: date = None) -> float:
    s, e = month_range(ref)
    return sum_by_type(db, family_id, record_type, s, e)


def today_expense(db: Session, family_id: Optional[int]) -> float:
    today = date.today()
    return sum_by_type(db, family_id, "expense", today, today)


def category_total(db: Session, family_id: Optional[int], category: str, ref: date = None) -> float:
    s, e = month_range(ref)
    q = _scope(
        db.query(func.coalesce(func.sum(FinancialRecord.amount), 0.0)),
        family_id,
    ).filter(
        FinancialRecord.record_type == "expense",
        FinancialRecord.category.ilike(f"%{category}%"),
        FinancialRecord.date >= s,
        FinancialRecord.date <= e,
    )
    return float(_completed(q).scalar() or 0)


def merchant_total(db: Session, family_id: Optional[int], merchant: str, ref: date = None) -> float:
    s, e = month_range(ref)
    q = _scope(
        db.query(func.coalesce(func.sum(FinancialRecord.amount), 0.0)),
        family_id,
    ).filter(
        FinancialRecord.merchant.ilike(f"%{merchant}%"),
        FinancialRecord.date >= s,
        FinancialRecord.date <= e,
    )
    return float(_completed(q).scalar() or 0)


def savings_rate(db: Session, family_id: Optional[int], ref: date = None) -> float:
    inc = month_total(db, family_id, "income", ref)
    sav = month_total(db, family_id, "savings", ref)
    if inc <= 0:
        return 0.0
    return round((sav / inc) * 100, 2)


def category_breakdown(db: Session, family_id: Optional[int], ref: date = None):
    s, e = month_range(ref)
    q = _scope(
        db.query(FinancialRecord.category, func.sum(FinancialRecord.amount)),
        family_id,
    ).filter(
        FinancialRecord.record_type == "expense",
        FinancialRecord.date >= s,
        FinancialRecord.date <= e,
        FinancialRecord.status == "completed",
    ).group_by(FinancialRecord.category)
    return [(c or "Others", float(v or 0)) for c, v in q.all()]


def status_count(db: Session, family_id: Optional[int], status: str) -> int:
    return _scope(db.query(FinancialRecord), family_id).filter(
        FinancialRecord.status == status
    ).count()
