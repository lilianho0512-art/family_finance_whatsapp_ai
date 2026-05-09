from datetime import date
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Family
from app.services import loan_service
from app.utils.currency import SUPPORTED_CURRENCIES
from app.utils.date_tools import parse_date
from app.routers.auth import get_optional_user, get_current_user

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))
from app.utils.currency import format_money as _fm
templates.env.filters["money"] = _fm


def _opt_float(v: str) -> Optional[float]:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _opt_int(v: str) -> Optional[int]:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _family_currency(db: Session, family_id: int) -> str:
    fam = db.query(Family).get(family_id)
    return (fam.default_currency if fam else "MYR") or "MYR"


@router.get("/loans", response_class=HTMLResponse)
def loans_page(request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    loans = loan_service.list_loans(db, user.family_id)
    monthly = loan_service.total_monthly_payment(db, user.family_id)
    outstanding = loan_service.total_outstanding(db, user.family_id)
    return templates.TemplateResponse(
        "loans.html",
        {
            "request": request,
            "user": user,
            "loans": loans,
            "monthly_total": monthly,
            "outstanding_total": outstanding,
            "today": date.today().isoformat(),
            "family_currency": _family_currency(db, user.family_id),
        },
    )


@router.get("/loans/new", response_class=HTMLResponse)
def loans_new(request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        "loan_form.html",
        {
            "request": request, "user": user, "loan": None,
            "today": date.today().isoformat(),
            "currencies": SUPPORTED_CURRENCIES,
            "family_currency": _family_currency(db, user.family_id),
        },
    )


@router.post("/loans")
def loans_create(
    request: Request,
    lender: str = Form(...),
    kind: str = Form("loan"),
    currency: str = Form("MYR"),
    principal: float = Form(...),
    monthly_payment: float = Form(...),
    interest_rate: str = Form(""),
    term_months: str = Form(""),
    start_date: str = Form(""),
    payment_due_day: str = Form(""),
    current_balance: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    loan_service.create_loan(
        db,
        user.family_id,
        lender=lender,
        kind=kind,
        currency=currency,
        principal=principal,
        monthly_payment=monthly_payment,
        interest_rate=_opt_float(interest_rate),
        term_months=_opt_int(term_months),
        start_date=parse_date(start_date) if start_date else None,
        payment_due_day=_opt_int(payment_due_day),
        current_balance=_opt_float(current_balance),
        notes=notes or None,
    )
    return RedirectResponse("/loans", status_code=303)


@router.get("/loans/{loan_id}/edit", response_class=HTMLResponse)
def loans_edit(loan_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    loan = loan_service.get_loan(db, user.family_id, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="not found")
    return templates.TemplateResponse(
        "loan_form.html",
        {
            "request": request, "user": user, "loan": loan,
            "today": date.today().isoformat(),
            "currencies": SUPPORTED_CURRENCIES,
            "family_currency": _family_currency(db, user.family_id),
        },
    )


@router.post("/loans/{loan_id}")
def loans_update(
    loan_id: int,
    request: Request,
    lender: str = Form(...),
    kind: str = Form("loan"),
    currency: str = Form("MYR"),
    principal: float = Form(...),
    monthly_payment: float = Form(...),
    interest_rate: str = Form(""),
    term_months: str = Form(""),
    start_date: str = Form(""),
    payment_due_day: str = Form(""),
    current_balance: str = Form(""),
    notes: str = Form(""),
    status: str = Form("active"),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    updated = loan_service.update_loan(
        db,
        user.family_id,
        loan_id,
        lender=lender.strip(),
        kind=kind,
        currency=currency,
        principal=principal,
        monthly_payment=monthly_payment,
        interest_rate=_opt_float(interest_rate),
        term_months=_opt_int(term_months),
        start_date=parse_date(start_date) if start_date else None,
        payment_due_day=_opt_int(payment_due_day),
        current_balance=_opt_float(current_balance),
        notes=notes or None,
        status=status,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return RedirectResponse("/loans", status_code=303)


@router.post("/loans/{loan_id}/close")
def loans_close(loan_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if loan_service.close_loan(db, user.family_id, loan_id) is None:
        raise HTTPException(status_code=404, detail="not found")
    return RedirectResponse("/loans", status_code=303)


@router.post("/loans/{loan_id}/delete")
def loans_delete(loan_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not loan_service.delete_loan(db, user.family_id, loan_id):
        raise HTTPException(status_code=404, detail="not found")
    return RedirectResponse("/loans", status_code=303)
