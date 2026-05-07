import time
import bcrypt
import jwt
from typing import Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models import User, Family, WhatsappEnrollment


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: int, family_id: int) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "fam": int(family_id),
        "iat": now,
        "exp": now + settings.JWT_EXPIRE_MINUTES * 60,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    if not token:
        return {}
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except Exception:
        return {}


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    if not email:
        return None
    return db.query(User).filter(User.email == email.lower().strip()).first()


def get_family(db: Session, family_id: int) -> Optional[Family]:
    return db.query(Family).get(family_id) if family_id else None


def get_enrollment_for_number(db: Session, whatsapp_number: str) -> Optional[WhatsappEnrollment]:
    if not whatsapp_number:
        return None
    return (
        db.query(WhatsappEnrollment)
        .filter(WhatsappEnrollment.whatsapp_number == whatsapp_number)
        .first()
    )
