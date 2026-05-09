from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.models import Family
from app.utils.currency import SUPPORTED_CURRENCIES, normalize
from app.routers.auth import get_optional_user, get_current_user

router = APIRouter()
templates = Jinja2Templates(directory=str(app_settings.BASE_DIR / "app" / "templates"))


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    family = db.query(Family).get(user.family_id)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": user,
            "family": family,
            "currencies": SUPPORTED_CURRENCIES,
            "saved": request.query_params.get("saved") == "1",
        },
    )


@router.post("/settings/currency")
def settings_set_currency(
    request: Request,
    default_currency: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    family = db.query(Family).get(user.family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="family not found")
    family.default_currency = normalize(default_currency)
    db.commit()
    return RedirectResponse("/settings?saved=1", status_code=303)
