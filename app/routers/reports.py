from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.services import record_service
from app.routers.auth import get_optional_user

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    family_id = user.family_id
    inc = record_service.month_total(db, family_id, "income")
    exp = record_service.month_total(db, family_id, "expense")
    sav = record_service.month_total(db, family_id, "savings")
    rate = record_service.savings_rate(db, family_id)
    cat = record_service.category_breakdown(db, family_id)
    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "user": user,
            "income": inc,
            "expense": exp,
            "savings": sav,
            "rate": rate,
            "categories": sorted(cat, key=lambda x: x[1], reverse=True),
        },
    )
