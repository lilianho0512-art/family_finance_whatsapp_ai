from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Family
from app.services import record_service, family_service, account_service
from app.utils import fx
from app.routers.auth import get_optional_user

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))
from app.utils.currency import format_money as _fm
templates.env.filters["money"] = _fm


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    family_id = user.family_id
    fam = db.query(Family).get(family_id)
    base_cur = fam.default_currency if fam else "MYR"

    # Grouped per currency, then converted to family default for the cards.
    inc_g = record_service.month_total_grouped(db, family_id, "income")
    exp_g = record_service.month_total_grouped(db, family_id, "expense")
    sav_g = record_service.month_total_grouped(db, family_id, "savings")
    today_g = record_service.today_expense_grouped(db, family_id)
    inc = fx.convert_grouped(inc_g, base_cur)
    exp = fx.convert_grouped(exp_g, base_cur)
    sav = fx.convert_grouped(sav_g, base_cur)
    today = fx.convert_grouped(today_g, base_cur)
    rate = round((sav / inc * 100), 2) if inc > 0 else 0.0
    # Whether totals are mixed-currency (drives the "converted" footnote)
    has_fx = any(len(g) > 1 or (g and base_cur not in g) for g in (inc_g, exp_g, sav_g, today_g))
    cat = record_service.category_breakdown(db, family_id)
    cat_sorted = sorted(cat, key=lambda x: x[1], reverse=True)
    top_cat = cat_sorted[0] if cat_sorted else ("-", 0)
    recent = record_service.list_recent(db, family_id, limit=10)
    need_q = record_service.status_count(db, family_id, "need_question")
    need_r = record_service.status_count(db, family_id, "need_review")
    enrollments = family_service.list_enrollments(db, family_id)
    account_balances = account_service.all_account_balances(db, family_id)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "family": fam,
            "income": inc,
            "expense": exp,
            "savings": sav,
            "rate": rate,
            "today": today,
            "top_cat": top_cat,
            "recent": recent,
            "need_q": need_q,
            "need_r": need_r,
            "categories": cat_sorted,
            "enrollments": enrollments,
            "account_balances": account_balances,
            "has_fx": has_fx,
            "income_by_cur": inc_g,
            "expense_by_cur": exp_g,
            "savings_by_cur": sav_g,
        },
    )
