from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models import Family, User, WhatsappEnrollment
from app.services.auth_service import hash_password


def create_family_with_admin(
    db: Session,
    family_name: str,
    email: str,
    password: str,
    whatsapp_number: str = "",
    label: str = "",
) -> Tuple[Family, User]:
    fam = Family(name=family_name.strip())
    db.add(fam)
    db.flush()
    user = User(
        family_id=fam.id,
        email=email.strip().lower(),
        password_hash=hash_password(password),
        role="admin",
    )
    db.add(user)
    db.flush()
    if whatsapp_number:
        enr = WhatsappEnrollment(
            family_id=fam.id,
            user_id=user.id,
            whatsapp_number=whatsapp_number.strip(),
            label=(label or "Admin").strip(),
        )
        db.add(enr)
    db.commit()
    db.refresh(fam)
    db.refresh(user)
    return fam, user


def add_whatsapp_number(
    db: Session,
    family_id: int,
    whatsapp_number: str,
    user_id: Optional[int] = None,
    label: str = "",
) -> WhatsappEnrollment:
    enr = WhatsappEnrollment(
        family_id=family_id,
        user_id=user_id,
        whatsapp_number=whatsapp_number.strip(),
        label=(label or "").strip(),
    )
    db.add(enr)
    db.commit()
    db.refresh(enr)
    return enr


def list_enrollments(db: Session, family_id: int):
    return (
        db.query(WhatsappEnrollment)
        .filter(WhatsappEnrollment.family_id == family_id)
        .order_by(WhatsappEnrollment.created_at.asc())
        .all()
    )


def remove_enrollment(db: Session, family_id: int, enrollment_id: int) -> bool:
    enr = (
        db.query(WhatsappEnrollment)
        .filter(
            WhatsappEnrollment.id == enrollment_id,
            WhatsappEnrollment.family_id == family_id,
        )
        .first()
    )
    if enr is None:
        return False
    db.delete(enr)
    db.commit()
    return True
