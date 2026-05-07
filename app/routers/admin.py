from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Family, User, WhatsappEnrollment, FinancialRecord, BugLog
from app.routers.auth import get_optional_user

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))


def _require_superadmin(request: Request, db: Session):
    user = get_optional_user(request, db)
    if user is None:
        return None, RedirectResponse("/login", status_code=303)
    if not user.is_superadmin:
        return None, RedirectResponse("/", status_code=303)
    return user, None


@router.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, db: Session = Depends(get_db)):
    user, redirect = _require_superadmin(request, db)
    if redirect is not None:
        return redirect

    families = db.query(Family).order_by(Family.created_at.asc()).all()
    fam_stats = []
    for f in families:
        n_users = db.query(User).filter(User.family_id == f.id).count()
        n_enr = db.query(WhatsappEnrollment).filter(WhatsappEnrollment.family_id == f.id).count()
        n_rec = db.query(FinancialRecord).filter(FinancialRecord.family_id == f.id).count()
        total = (
            db.query(func.coalesce(func.sum(FinancialRecord.amount), 0.0))
            .filter(
                FinancialRecord.family_id == f.id,
                FinancialRecord.status == "completed",
            )
            .scalar()
        )
        fam_stats.append({
            "family": f,
            "users": n_users,
            "enrollments": n_enr,
            "records": n_rec,
            "total": float(total or 0),
        })

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": user,
            "fam_stats": fam_stats,
            "user_count": db.query(User).count(),
            "record_count": db.query(FinancialRecord).count(),
            "bug_count": db.query(BugLog).count(),
            "enrollment_count": db.query(WhatsappEnrollment).count(),
            "recent_bugs": db.query(BugLog).order_by(BugLog.created_at.desc()).limit(10).all(),
        },
    )


@router.get("/admin/family/{family_id}", response_class=HTMLResponse)
def admin_family_detail(family_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = _require_superadmin(request, db)
    if redirect is not None:
        return redirect

    fam = db.query(Family).get(family_id)
    if fam is None:
        raise HTTPException(status_code=404, detail="family not found")
    members = db.query(User).filter(User.family_id == family_id).all()
    enrollments = (
        db.query(WhatsappEnrollment)
        .filter(WhatsappEnrollment.family_id == family_id)
        .order_by(WhatsappEnrollment.created_at.asc())
        .all()
    )
    records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.family_id == family_id)
        .order_by(FinancialRecord.created_at.desc())
        .limit(200)
        .all()
    )
    return templates.TemplateResponse(
        "admin_family.html",
        {
            "request": request,
            "user": user,
            "family": fam,
            "members": members,
            "enrollments": enrollments,
            "records": records,
        },
    )


@router.get("/admin/bugs", response_class=HTMLResponse)
def admin_bugs(request: Request, db: Session = Depends(get_db)):
    user, redirect = _require_superadmin(request, db)
    if redirect is not None:
        return redirect

    bugs = db.query(BugLog).order_by(BugLog.created_at.desc()).limit(200).all()
    return templates.TemplateResponse(
        "admin_bugs.html",
        {"request": request, "user": user, "bugs": bugs},
    )
