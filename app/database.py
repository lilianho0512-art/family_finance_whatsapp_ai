from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables directly from SQLAlchemy metadata.

    This is a quickstart fallback. The supported way to manage schema is
    Alembic (`alembic upgrade head`). `run_migrations()` should be preferred
    for fresh installs and upgrades; `init_db()` is kept for tests and as a
    last-resort fallback if Alembic is unavailable.
    """
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def run_migrations() -> bool:
    """Apply Alembic migrations up to head. Returns True on success."""
    from pathlib import Path
    try:
        from alembic.config import Config
        from alembic import command
    except ImportError:
        return False
    base = Path(__file__).resolve().parent.parent
    cfg = Config(str(base / "alembic.ini"))
    cfg.set_main_option("script_location", str(base / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    command.upgrade(cfg, "head")
    return True
