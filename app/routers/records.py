from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import FinancialRecord
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


@router.delete("/records/{record_id}")
def delete_record(record_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    rec = db.query(FinancialRecord).get(record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="record not found")
    if not user.is_superadmin and rec.family_id != user.family_id:
        raise HTTPException(status_code=404, detail="record not found")
    db.delete(rec)
    db.commit()
    return {"status": "deleted", "id": record_id}
