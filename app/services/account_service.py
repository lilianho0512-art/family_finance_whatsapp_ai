"""Bank-account ledger: registry of accounts + balance snapshots + balance compute."""
from datetime import date
from typing import List, Optional, Dict
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import BankAccount, AccountBalance, FinancialRecord


def list_accounts(db: Session, family_id: int) -> List[BankAccount]:
    return (
        db.query(BankAccount)
        .filter(BankAccount.family_id == family_id, BankAccount.is_active == 1)
        .order_by(BankAccount.created_at.asc())
        .all()
    )


def ensure_account(db: Session, family_id: int, name: str) -> BankAccount:
    """Auto-create a bank account row if not seen before. Idempotent."""
    name = (name or "").strip()
    if not name:
        return None
    existing = (
        db.query(BankAccount)
        .filter(BankAccount.family_id == family_id, BankAccount.name == name)
        .first()
    )
    if existing is not None:
        if existing.is_active != 1:
            existing.is_active = 1
            db.commit()
            db.refresh(existing)
        return existing
    acc = BankAccount(family_id=family_id, name=name, is_active=1)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


def deactivate_account(db: Session, family_id: int, account_id: int) -> bool:
    acc = (
        db.query(BankAccount)
        .filter(BankAccount.id == account_id, BankAccount.family_id == family_id)
        .first()
    )
    if acc is None:
        return False
    acc.is_active = 0
    db.commit()
    return True


def add_balance_snapshot(
    db: Session, family_id: int, account_name: str, balance: float,
    as_of: Optional[date] = None, note: str = ""
) -> AccountBalance:
    snap = AccountBalance(
        family_id=family_id,
        account_name=account_name.strip(),
        as_of_date=as_of or date.today(),
        balance=float(balance),
        note=note,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    # Auto-register the account if not already
    ensure_account(db, family_id, account_name)
    return snap


def latest_snapshot(db: Session, family_id: int, account_name: str) -> Optional[AccountBalance]:
    return (
        db.query(AccountBalance)
        .filter(
            AccountBalance.family_id == family_id,
            AccountBalance.account_name == account_name,
        )
        .order_by(AccountBalance.as_of_date.desc(), AccountBalance.created_at.desc())
        .first()
    )


def list_snapshots(db: Session, family_id: int, account_name: Optional[str] = None,
                   limit: int = 50) -> List[AccountBalance]:
    q = db.query(AccountBalance).filter(AccountBalance.family_id == family_id)
    if account_name:
        q = q.filter(AccountBalance.account_name == account_name)
    return q.order_by(AccountBalance.as_of_date.desc(), AccountBalance.created_at.desc()).limit(limit).all()


def delete_snapshot(db: Session, family_id: int, snapshot_id: int) -> bool:
    snap = (
        db.query(AccountBalance)
        .filter(AccountBalance.id == snapshot_id, AccountBalance.family_id == family_id)
        .first()
    )
    if snap is None:
        return False
    db.delete(snap)
    db.commit()
    return True


def _flow_after(db: Session, family_id: int, account_name: str,
                from_date: Optional[date], record_type: str) -> float:
    q = db.query(func.coalesce(func.sum(FinancialRecord.amount), 0.0)).filter(
        FinancialRecord.family_id == family_id,
        FinancialRecord.account == account_name,
        FinancialRecord.record_type == record_type,
        FinancialRecord.status == "completed",
    )
    if from_date is not None:
        q = q.filter(FinancialRecord.date > from_date)
    return float(q.scalar() or 0)


def computed_balance(db: Session, family_id: int, account_name: str) -> Dict:
    """
    balance = latest_snapshot + (incomes_in - expenses_out + savings_in) since snapshot.

    Note: savings is treated as ARRIVING at this account (e.g. money parked in
    UOB savings adds to UOB balance). Transfers are not modelled (single-account).
    """
    snap = latest_snapshot(db, family_id, account_name)
    snap_balance = float(snap.balance) if snap else 0.0
    snap_date = snap.as_of_date if snap else None

    inc = _flow_after(db, family_id, account_name, snap_date, "income")
    exp = _flow_after(db, family_id, account_name, snap_date, "expense")
    sav = _flow_after(db, family_id, account_name, snap_date, "savings")
    computed = snap_balance + inc - exp + sav

    return {
        "account": account_name,
        "snapshot_balance": snap_balance,
        "snapshot_date": snap_date.isoformat() if snap_date else None,
        "income_since": inc,
        "expense_since": exp,
        "savings_since": sav,
        "computed_balance": round(computed, 2),
    }


def all_account_balances(db: Session, family_id: int) -> List[Dict]:
    """Return computed balance for every account that's been seen
    (registered OR appearing in a record/snapshot)."""
    seen = set()
    for a in list_accounts(db, family_id):
        seen.add(a.name)
    rows = (
        db.query(FinancialRecord.account)
        .filter(FinancialRecord.family_id == family_id, FinancialRecord.account.isnot(None))
        .distinct()
        .all()
    )
    for (name,) in rows:
        if name:
            seen.add(name)
    rows = (
        db.query(AccountBalance.account_name)
        .filter(AccountBalance.family_id == family_id)
        .distinct()
        .all()
    )
    for (name,) in rows:
        if name:
            seen.add(name)
    return [computed_balance(db, family_id, n) for n in sorted(seen)]
