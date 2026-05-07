from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import excel_export
from app.routers.auth import get_optional_user

router = APIRouter()


@router.get("/export/monthly")
def export_monthly(request: Request, db: Session = Depends(get_db)):
    user = get_optional_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    path = excel_export.export_monthly(db, user.family_id)
    return FileResponse(
        path,
        filename="monthly_finance_report.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
