from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.services import record_service
from app.routers.auth import get_optional_user

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))


@router.get("/records", response_class=HTMLResponse)
def records_page(request: Request, status: str = Query(None), db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    items = record_service.list_all(db, user.family_id, status=status)
    return templates.TemplateResponse(
        "records.html",
        {"request": request, "user": user, "records": items, "status": status or ""},
    )
