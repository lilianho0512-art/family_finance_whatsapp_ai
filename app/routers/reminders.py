from datetime import date
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services import recurring_expense_service, reminder_service
from app.routers.auth import get_optional_user, get_current_user

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))


@router.get("/reminders", response_class=HTMLResponse)
def reminders_page(request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    today = date.today()
    upcoming = reminder_service.upcoming_for_family(db, user.family_id, today=today, days_ahead=14)
    recurring = recurring_expense_service.list_recurring(db, user.family_id)
    history = reminder_service.recent_reminders(db, user.family_id, limit=30)
    return templates.TemplateResponse(
        "reminders.html",
        {
            "request": request,
            "user": user,
            "today": today,
            "upcoming": upcoming,
            "recurring": recurring,
            "history": history,
            "monthly_total": recurring_expense_service.total_monthly(db, user.family_id),
        },
    )


@router.post("/reminders/recurring")
def reminders_recurring_create(
    request: Request,
    name: str = Form(...),
    amount: float = Form(...),
    payment_due_day: int = Form(...),
    category: str = Form(""),
    account: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not name.strip():
        raise HTTPException(status_code=400, detail="name required")
    recurring_expense_service.create_recurring(
        db, user.family_id,
        name=name, amount=amount, payment_due_day=payment_due_day,
        category=category or None, account=account or None, notes=notes or None,
    )
    return RedirectResponse("/reminders", status_code=303)


@router.post("/reminders/recurring/{item_id}")
def reminders_recurring_update(
    item_id: int,
    request: Request,
    name: str = Form(...),
    amount: float = Form(...),
    payment_due_day: int = Form(...),
    category: str = Form(""),
    account: str = Form(""),
    notes: str = Form(""),
    status: str = Form("active"),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    updated = recurring_expense_service.update_recurring(
        db, user.family_id, item_id,
        name=name.strip(), amount=amount, payment_due_day=payment_due_day,
        category=category or None, account=account or None, notes=notes or None,
        status=status,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return RedirectResponse("/reminders", status_code=303)


@router.post("/reminders/recurring/{item_id}/delete")
def reminders_recurring_delete(item_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not recurring_expense_service.delete_recurring(db, user.family_id, item_id):
        raise HTTPException(status_code=404, detail="not found")
    return RedirectResponse("/reminders", status_code=303)


@router.post("/reminders/run-now")
def reminders_run_now(request: Request, db: Session = Depends(get_db)):
    """Manual trigger — fires the daily reminder pass for this family right now.
    Useful for testing without waiting for 09:00. Dedup still applies: items
    already reminded for today's slot won't be re-sent."""
    user = get_current_user(request, db)
    sent, skipped = reminder_service.run_for_family(db, user.family_id)
    return JSONResponse({"sent": sent, "skipped_as_dup": skipped})
