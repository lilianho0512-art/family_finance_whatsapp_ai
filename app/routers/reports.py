from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Family
from app.services import record_service
from app.utils import fx
from app.routers.auth import get_optional_user

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))
from app.utils.currency import format_money as _fm
templates.env.filters["money"] = _fm


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    family_id = user.family_id
    fam = db.query(Family).get(family_id)
    base_cur = fam.default_currency if fam else "MYR"
    inc_g = record_service.month_total_grouped(db, family_id, "income")
    exp_g = record_service.month_total_grouped(db, family_id, "expense")
    sav_g = record_service.month_total_grouped(db, family_id, "savings")
    inc = fx.convert_grouped(inc_g, base_cur)
    exp = fx.convert_grouped(exp_g, base_cur)
    sav = fx.convert_grouped(sav_g, base_cur)
    rate = round((sav / inc * 100), 2) if inc > 0 else 0.0
    cat = record_service.category_breakdown(db, family_id)
    has_fx = any(len(g) > 1 or (g and base_cur not in g) for g in (inc_g, exp_g, sav_g))
    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "user": user,
            "family": fam,
            "income": inc,
            "expense": exp,
            "savings": sav,
            "rate": rate,
            "categories": sorted(cat, key=lambda x: x[1], reverse=True),
            "income_by_cur": inc_g,
            "expense_by_cur": exp_g,
            "savings_by_cur": sav_g,
            "has_fx": has_fx,
        },
    )
