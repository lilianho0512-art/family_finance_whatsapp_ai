from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Loan

VALID_KINDS = ("loan", "installment")
VALID_STATUSES = ("active", "closed")


def list_loans(db: Session, family_id: int, include_closed: bool = True) -> List[Loan]:
    q = db.query(Loan).filter(Loan.family_id == family_id)
    if not include_closed:
        q = q.filter(Loan.status == "active")
    return q.order_by(Loan.status.asc(), Loan.start_date.desc().nulls_last(), Loan.id.desc()).all()


def get_loan(db: Session, family_id: int, loan_id: int) -> Optional[Loan]:
    return (
        db.query(Loan)
        .filter(Loan.id == loan_id, Loan.family_id == family_id)
        .first()
    )


def create_loan(
    db: Session,
    family_id: int,
    *,
    lender: str,
    principal: float,
    monthly_payment: float,
    kind: str = "loan",
    currency: str = "MYR",
    interest_rate: Optional[float] = None,
    term_months: Optional[int] = None,
    start_date: Optional[date] = None,
    payment_due_day: Optional[int] = None,
    current_balance: Optional[float] = None,
    notes: Optional[str] = None,
) -> Loan:
    from app.utils.currency import normalize as _norm_currency
    if kind not in VALID_KINDS:
        kind = "loan"
    if payment_due_day is not None and not (1 <= payment_due_day <= 31):
        payment_due_day = None
    loan = Loan(
        family_id=family_id,
        kind=kind,
        lender=lender.strip(),
        currency=_norm_currency(currency),
        principal=float(principal or 0),
        interest_rate=interest_rate,
        term_months=term_months,
        monthly_payment=float(monthly_payment or 0),
        start_date=start_date,
        payment_due_day=payment_due_day,
        current_balance=float(current_balance if current_balance is not None else (principal or 0)),
        status="active",
        notes=notes,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def update_loan(db: Session, family_id: int, loan_id: int, **fields) -> Optional[Loan]:
    from app.utils.currency import normalize as _norm_currency
    loan = get_loan(db, family_id, loan_id)
    if loan is None:
        return None
    if "kind" in fields and fields["kind"] not in VALID_KINDS:
        fields.pop("kind")
    if "status" in fields and fields["status"] not in VALID_STATUSES:
        fields.pop("status")
    if "payment_due_day" in fields:
        d = fields["payment_due_day"]
        if d is not None and not (1 <= int(d) <= 31):
            fields["payment_due_day"] = None
    if "currency" in fields and fields["currency"] is not None:
        fields["currency"] = _norm_currency(fields["currency"])
    for k, v in fields.items():
        if hasattr(loan, k) and v is not None:
            setattr(loan, k, v)
    db.commit()
    db.refresh(loan)
    return loan


def close_loan(db: Session, family_id: int, loan_id: int) -> Optional[Loan]:
    loan = get_loan(db, family_id, loan_id)
    if loan is None:
        return None
    loan.status = "closed"
    loan.current_balance = 0.0
    db.commit()
    db.refresh(loan)
    return loan


def delete_loan(db: Session, family_id: int, loan_id: int) -> bool:
    loan = get_loan(db, family_id, loan_id)
    if loan is None:
        return False
    db.delete(loan)
    db.commit()
    return True


def total_monthly_payment(db: Session, family_id: int) -> float:
    rows = (
        db.query(Loan)
        .filter(Loan.family_id == family_id, Loan.status == "active")
        .all()
    )
    return round(sum(float(r.monthly_payment or 0) for r in rows), 2)


def total_outstanding(db: Session, family_id: int) -> float:
    rows = (
        db.query(Loan)
        .filter(Loan.family_id == family_id, Loan.status == "active")
        .all()
    )
    return round(sum(float(r.current_balance or 0) for r in rows), 2)
