from datetime import date
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Family
from app.services import account_service
from app.utils.date_tools import parse_date
from app.routers.auth import get_optional_user, get_current_user

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))
from app.utils.currency import format_money as _fm
templates.env.filters["money"] = _fm


@router.get("/accounts", response_class=HTMLResponse)
def accounts_page(request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    rows = account_service.all_account_balances(db, user.family_id)
    accounts = account_service.list_accounts(db, user.family_id)
    snapshots = account_service.list_snapshots(db, user.family_id, limit=30)
    fam = db.query(Family).get(user.family_id)
    return templates.TemplateResponse(
        "accounts.html",
        {
            "request": request,
            "user": user,
            "family": fam,
            "rows": rows,
            "accounts": accounts,
            "snapshots": snapshots,
            "today": date.today().isoformat(),
        },
    )


@router.post("/accounts/add")
def accounts_add(
    name: str = Form(...),
    note: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    acc = account_service.ensure_account(db, user.family_id, name)
    if note:
        acc.note = note
        db.commit()
    return RedirectResponse("/accounts", status_code=303)


@router.post("/accounts/{account_id}/delete")
def accounts_delete(
    account_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not account_service.deactivate_account(db, user.family_id, account_id):
        raise HTTPException(status_code=404, detail="not found")
    return RedirectResponse("/accounts", status_code=303)


@router.post("/accounts/snapshot")
def accounts_snapshot(
    account_name: str = Form(...),
    balance: float = Form(...),
    as_of_date: str = Form(""),
    note: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    as_of = parse_date(as_of_date) if as_of_date else date.today()
    account_service.add_balance_snapshot(
        db, user.family_id, account_name.strip(), balance, as_of=as_of, note=note
    )
    return RedirectResponse("/accounts", status_code=303)


@router.post("/accounts/snapshot/{snapshot_id}/delete")
def accounts_snapshot_delete(
    snapshot_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not account_service.delete_snapshot(db, user.family_id, snapshot_id):
        raise HTTPException(status_code=404, detail="not found")
    return RedirectResponse("/accounts", status_code=303)
