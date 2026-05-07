from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, Family, WhatsappEnrollment
from app.services import auth_service, family_service

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))

COOKIE_NAME = "ff_token"


def _extract_token(request: Request) -> Optional[str]:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = auth_service.decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).get(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


def _set_token_cookie(response, token: str):
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    if db.query(User).count() == 0:
        return RedirectResponse("/register", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = auth_service.get_user_by_email(db, email)
    if not user or not auth_service.verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "邮箱或密码错误"},
            status_code=401,
        )
    token = auth_service.create_token(user.id, user.family_id)
    resp = RedirectResponse("/", status_code=303)
    _set_token_cookie(resp, token)
    return resp


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register")
def register(
    request: Request,
    family_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    whatsapp_number: str = Form(""),
    label: str = Form(""),
    db: Session = Depends(get_db),
):
    email = (email or "").strip().lower()
    if not email or len(password) < 6:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "邮箱不可空，密码至少 6 位"},
            status_code=400,
        )
    if auth_service.get_user_by_email(db, email):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "邮箱已注册"},
            status_code=409,
        )
    if whatsapp_number.strip():
        existing = (
            db.query(WhatsappEnrollment)
            .filter(WhatsappEnrollment.whatsapp_number == whatsapp_number.strip())
            .first()
        )
        if existing:
            return templates.TemplateResponse(
                "register.html",
                {"request": request, "error": "该 WhatsApp 号已绑定其他家庭"},
                status_code=409,
            )
    fam, user = family_service.create_family_with_admin(
        db,
        family_name=family_name,
        email=email,
        password=password,
        whatsapp_number=whatsapp_number,
        label=label,
    )
    token = auth_service.create_token(user.id, fam.id)
    resp = RedirectResponse("/", status_code=303)
    _set_token_cookie(resp, token)
    return resp


@router.get("/auth/logout")
@router.post("/auth/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


@router.get("/auth/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fam = db.query(Family).get(user.family_id)
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "family_id": user.family_id,
        "family_name": fam.name if fam else "",
    }


@router.post("/auth/login")
def api_login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """JSON token endpoint for API/CLI clients."""
    user = auth_service.get_user_by_email(db, email)
    if not user or not auth_service.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = auth_service.create_token(user.id, user.family_id)
    return {"access_token": token, "token_type": "bearer",
            "expires_in": settings.JWT_EXPIRE_MINUTES * 60}


@router.post("/auth/whatsapp")
def add_whatsapp(
    whatsapp_number: str = Form(...),
    label: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number = whatsapp_number.strip()
    existing = (
        db.query(WhatsappEnrollment)
        .filter(WhatsappEnrollment.whatsapp_number == number)
        .first()
    )
    if existing:
        if existing.family_id != user.family_id:
            raise HTTPException(status_code=409, detail="号码已绑定其他家庭")
        return JSONResponse({"status": "already_enrolled", "id": existing.id})
    enr = family_service.add_whatsapp_number(
        db, family_id=user.family_id, whatsapp_number=number, user_id=user.id, label=label
    )
    return {"status": "ok", "id": enr.id, "whatsapp_number": enr.whatsapp_number}


@router.delete("/auth/whatsapp/{enrollment_id}")
def delete_whatsapp(
    enrollment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok = family_service.remove_enrollment(db, user.family_id, enrollment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="not found")
    return {"status": "deleted"}
