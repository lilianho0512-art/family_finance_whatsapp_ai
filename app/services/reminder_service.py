"""Daily reminder engine for upcoming payments.

Two sources are reminded on:
  - active loans (Loan.payment_due_day)
  - active recurring expenses (RecurringExpense.payment_due_day)

Two reminder kinds:
  - "day_before" — fired when due_date == today + 1
  - "day_of"    — fired when due_date == today

Dedup is enforced by the UNIQUE constraint on
(family_id, target_type, target_id, due_date, kind) in payment_reminders;
the scheduler can be re-run on the same day without duplicates.
"""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Family, Loan, PaymentReminder, RecurringExpense, WhatsappEnrollment
from app.services import whatsapp_service
from app.utils.logger import logger
from app.utils.money_tools import format_money


@dataclass
class UpcomingItem:
    family_id: int
    target_type: str       # "loan" | "recurring"
    target_id: int
    name: str
    amount: float
    due_date: date
    currency: str = "MYR"


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def _last_day(year: int, month: int) -> int:
    return monthrange(year, month)[1]


def clamp_due_day_to_month(due_day: int, year: int, month: int) -> int:
    """Map e.g. due_day=31 in February to Feb 28/29 (last day of that month)."""
    return min(int(due_day or 1), _last_day(year, month))


def compute_next_due(due_day: int, today: date) -> date:
    """Return the next occurrence (>= today) of `due_day` in the calendar.

    If today's day is <= due_day (clamped to month-end) the next due falls
    in the current month; otherwise it rolls to next month.
    """
    this_month_due = today.replace(day=clamp_due_day_to_month(due_day, today.year, today.month))
    if this_month_due >= today:
        return this_month_due
    # Roll to next month
    if today.month == 12:
        year, month = today.year + 1, 1
    else:
        year, month = today.year, today.month + 1
    return date(year, month, clamp_due_day_to_month(due_day, year, month))


# ---------------------------------------------------------------------------
# Listing upcoming items
# ---------------------------------------------------------------------------


def upcoming_for_family(
    db: Session, family_id: int, today: Optional[date] = None, days_ahead: int = 14
) -> List[UpcomingItem]:
    """All active loans + recurring expenses with their next due date,
    sorted earliest-first, limited to items due within `days_ahead`."""
    today = today or date.today()
    horizon = today + timedelta(days=days_ahead)

    items: List[UpcomingItem] = []

    loans = (
        db.query(Loan)
        .filter(
            Loan.family_id == family_id,
            Loan.status == "active",
            Loan.payment_due_day.isnot(None),
        )
        .all()
    )
    for l in loans:
        due = compute_next_due(l.payment_due_day, today)
        if due <= horizon:
            items.append(UpcomingItem(
                family_id=family_id, target_type="loan", target_id=l.id,
                name=l.lender, amount=float(l.monthly_payment or 0), due_date=due,
                currency=(l.currency or "MYR"),
            ))

    recurring = (
        db.query(RecurringExpense)
        .filter(RecurringExpense.family_id == family_id, RecurringExpense.status == "active")
        .all()
    )
    for r in recurring:
        due = compute_next_due(r.payment_due_day, today)
        if due <= horizon:
            items.append(UpcomingItem(
                family_id=family_id, target_type="recurring", target_id=r.id,
                name=r.name, amount=float(r.amount or 0), due_date=due,
                currency=(r.currency or "MYR"),
            ))

    items.sort(key=lambda x: (x.due_date, x.target_type, x.target_id))
    return items


# ---------------------------------------------------------------------------
# Sending reminders
# ---------------------------------------------------------------------------


def format_message(item: UpcomingItem, kind: str) -> str:
    """Compose the reminder text the user receives."""
    label = "Loan" if item.target_type == "loan" else "Bill"
    when = "TODAY" if kind == "day_of" else "TOMORROW"
    return (
        f"🔔 Payment due {when} ({item.due_date.isoformat()})\n"
        f"{label}: {item.name}\n"
        f"Amount: {format_money(item.amount, item.currency)}"
    )


def _enrollment_numbers(db: Session, family_id: int) -> List[str]:
    rows = (
        db.query(WhatsappEnrollment)
        .filter(WhatsappEnrollment.family_id == family_id)
        .all()
    )
    return [r.whatsapp_number for r in rows if r.whatsapp_number]


def _mark_reminded(
    db: Session,
    item: UpcomingItem,
    kind: str,
    message: str,
    status: str = "sent",
) -> bool:
    """Insert a PaymentReminder; returns False if the row already exists
    (UNIQUE violation), which means we already reminded for this slot."""
    rec = PaymentReminder(
        family_id=item.family_id,
        target_type=item.target_type,
        target_id=item.target_id,
        due_date=item.due_date,
        kind=kind,
        sent_at=datetime.utcnow(),
        status=status,
        message=message[:2000],
    )
    db.add(rec)
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def _send_for_item(db: Session, item: UpcomingItem, kind: str) -> bool:
    """Insert dedup row first; if accepted, fire the messages. Returns True if
    we actually sent (or attempted) for this slot, False if it was a dup."""
    msg = format_message(item, kind)
    if not _mark_reminded(db, item, kind, msg):
        return False  # already reminded today

    numbers = _enrollment_numbers(db, item.family_id)
    if not numbers:
        logger.info(
            f"[reminder] family={item.family_id} {item.target_type}#{item.target_id} "
            f"({item.name}) no enrollments — message logged only"
        )
        return True

    delivered_any = False
    for num in numbers:
        try:
            ok = whatsapp_service.send_text(num, msg)
            delivered_any = delivered_any or bool(ok)
        except Exception as e:
            logger.warning(f"[reminder] send to {num} failed: {e}")

    if not delivered_any:
        # Mark the row as failed so the UI can show it (we don't roll back the
        # dedup row — sending again would just spam if the failure persists).
        try:
            row = (
                db.query(PaymentReminder)
                .filter(
                    PaymentReminder.family_id == item.family_id,
                    PaymentReminder.target_type == item.target_type,
                    PaymentReminder.target_id == item.target_id,
                    PaymentReminder.due_date == item.due_date,
                    PaymentReminder.kind == kind,
                )
                .first()
            )
            if row is not None:
                row.status = "failed"
                db.commit()
        except Exception:
            db.rollback()
    return True


def run_for_family(db: Session, family_id: int, today: Optional[date] = None) -> Tuple[int, int]:
    """Send any due reminders for one family. Returns (sent, skipped_as_dup)."""
    today = today or date.today()
    sent = 0
    skipped = 0

    # Day-before: items due tomorrow (today + 1)
    for item in upcoming_for_family(db, family_id, today=today, days_ahead=1):
        if item.due_date == today + timedelta(days=1):
            if _send_for_item(db, item, "day_before"):
                sent += 1
            else:
                skipped += 1

    # Day-of: items due today
    for item in upcoming_for_family(db, family_id, today=today, days_ahead=0):
        if item.due_date == today:
            if _send_for_item(db, item, "day_of"):
                sent += 1
            else:
                skipped += 1

    return sent, skipped


def run_daily_reminders(today: Optional[date] = None) -> None:
    """Entry point for the APScheduler job. Iterates every family."""
    from app.database import SessionLocal
    today = today or date.today()
    db = SessionLocal()
    try:
        families: Iterable[Family] = db.query(Family).all()
        total_sent = total_skipped = 0
        for fam in families:
            try:
                s, k = run_for_family(db, fam.id, today=today)
                total_sent += s
                total_skipped += k
            except Exception as e:
                logger.error(f"[reminder] family={fam.id} failed: {e}")
        logger.info(
            f"[reminder] daily run complete — sent={total_sent} dup_skipped={total_skipped}"
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------


def recent_reminders(db: Session, family_id: int, limit: int = 30):
    return (
        db.query(PaymentReminder)
        .filter(PaymentReminder.family_id == family_id)
        .order_by(PaymentReminder.sent_at.desc())
        .limit(limit)
        .all()
    )
