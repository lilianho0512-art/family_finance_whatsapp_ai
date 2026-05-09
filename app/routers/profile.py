from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Family, WhatsappEnrollment
from app.services import auth_service, family_service
from app.routers.auth import get_optional_user, get_current_user

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))


def _list_user_enrollments(db: Session, family_id: int, user_id: int):
    """Numbers explicitly linked to this user, plus family enrollments
    with no owner so the current user can claim them."""
    return (
        db.query(WhatsappEnrollment)
        .filter(WhatsappEnrollment.family_id == family_id)
        .filter((WhatsappEnrollment.user_id == user_id) | (WhatsappEnrollment.user_id.is_(None)))
        .order_by(WhatsappEnrollment.created_at.asc())
        .all()
    )


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    family = db.query(Family).get(user.family_id)
    enrollments = _list_user_enrollments(db, user.family_id, user.id)
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "family": family,
            "enrollments": enrollments,
            "saved": request.query_params.get("saved") == "1",
            "error": request.query_params.get("error") or None,
            "added": request.query_params.get("added") == "1",
            "removed": request.query_params.get("removed") == "1",
        },
    )


@router.post("/profile/password")
def profile_change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if new_password != confirm_password:
        return RedirectResponse("/profile?error=Passwords+do+not+match", status_code=303)
    ok, err = auth_service.change_password(db, user, old_password, new_password)
    if not ok:
        from urllib.parse import quote
        return RedirectResponse(f"/profile?error={quote(err)}", status_code=303)
    return RedirectResponse("/profile?saved=1", status_code=303)


@router.post("/profile/whatsapp")
def profile_add_whatsapp(
    request: Request,
    whatsapp_number: str = Form(...),
    label: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    number = (whatsapp_number or "").strip()
    if not number:
        return RedirectResponse("/profile?error=Number+required", status_code=303)
    existing = (
        db.query(WhatsappEnrollment)
        .filter(WhatsappEnrollment.whatsapp_number == number)
        .first()
    )
    if existing:
        if existing.family_id != user.family_id:
            from urllib.parse import quote
            return RedirectResponse(
                f"/profile?error={quote('That number is already linked to another family')}",
                status_code=303,
            )
        # Reuse existing enrollment, just claim it for this user
        existing.user_id = user.id
        if label:
            existing.label = label.strip()
        db.commit()
        return RedirectResponse("/profile?added=1", status_code=303)
    family_service.add_whatsapp_number(
        db, family_id=user.family_id, whatsapp_number=number, user_id=user.id, label=label
    )
    return RedirectResponse("/profile?added=1", status_code=303)


@router.post("/profile/whatsapp/{enrollment_id}/delete")
def profile_remove_whatsapp(
    enrollment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not family_service.remove_enrollment(db, user.family_id, enrollment_id):
        raise HTTPException(status_code=404, detail="not found")
    return RedirectResponse("/profile?removed=1", status_code=303)
