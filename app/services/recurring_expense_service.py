from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import RecurringExpense

VALID_STATUSES = ("active", "paused")


def _clamp_due_day(d) -> int:
    try:
        n = int(d)
    except (TypeError, ValueError):
        return 1
    return max(1, min(31, n))


def list_recurring(db: Session, family_id: int, include_paused: bool = True) -> List[RecurringExpense]:
    q = db.query(RecurringExpense).filter(RecurringExpense.family_id == family_id)
    if not include_paused:
        q = q.filter(RecurringExpense.status == "active")
    return q.order_by(RecurringExpense.status.asc(), RecurringExpense.payment_due_day.asc(), RecurringExpense.id.desc()).all()


def get_recurring(db: Session, family_id: int, item_id: int) -> Optional[RecurringExpense]:
    return (
        db.query(RecurringExpense)
        .filter(RecurringExpense.id == item_id, RecurringExpense.family_id == family_id)
        .first()
    )


def create_recurring(
    db: Session,
    family_id: int,
    *,
    name: str,
    amount: float,
    payment_due_day: int,
    currency: str = "MYR",
    category: Optional[str] = None,
    account: Optional[str] = None,
    notes: Optional[str] = None,
) -> RecurringExpense:
    from app.utils.currency import normalize as _norm_currency
    item = RecurringExpense(
        family_id=family_id,
        name=name.strip(),
        amount=float(amount or 0),
        currency=_norm_currency(currency),
        payment_due_day=_clamp_due_day(payment_due_day),
        category=(category or None),
        account=(account or None),
        status="active",
        notes=notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_recurring(db: Session, family_id: int, item_id: int, **fields) -> Optional[RecurringExpense]:
    item = get_recurring(db, family_id, item_id)
    if item is None:
        return None
    if "status" in fields and fields["status"] not in VALID_STATUSES:
        fields.pop("status")
    if "payment_due_day" in fields and fields["payment_due_day"] is not None:
        fields["payment_due_day"] = _clamp_due_day(fields["payment_due_day"])
    if "currency" in fields and fields["currency"] is not None:
        from app.utils.currency import normalize as _norm_currency
        fields["currency"] = _norm_currency(fields["currency"])
    for k, v in fields.items():
        if hasattr(item, k) and v is not None:
            setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


def delete_recurring(db: Session, family_id: int, item_id: int) -> bool:
    item = get_recurring(db, family_id, item_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def total_monthly(db: Session, family_id: int) -> float:
    rows = (
        db.query(RecurringExpense)
        .filter(RecurringExpense.family_id == family_id, RecurringExpense.status == "active")
        .all()
    )
    return round(sum(float(r.amount or 0) for r in rows), 2)
