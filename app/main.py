from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, run_migrations
from app.services.self_healing_service import ensure_folders, health_summary
from app.services import scheduler_service
from app.routers import whatsapp, dashboard, records, reports, export, auth, admin, accounts, loans, reminders, settings as settings_router
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_folders()
    try:
        if run_migrations():
            logger.info("Alembic migrations applied (or already up to date)")
        else:
            init_db()
            logger.warning("Alembic unavailable — fell back to create_all()")
    except Exception as e:
        logger.error(f"Migration failed, falling back to create_all(): {e}")
        init_db()
    scheduler_service.start()
    logger.info("Family Finance WhatsApp AI Assistant started")
    try:
        yield
    finally:
        scheduler_service.shutdown()
        logger.info("Family Finance WhatsApp AI Assistant stopped")


app = FastAPI(title="Family Finance WhatsApp AI Assistant", lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=str(settings.BASE_DIR / "app" / "static")),
    name="static",
)
app.include_router(auth.router, tags=["auth"])
app.include_router(admin.router, tags=["admin"])
app.include_router(whatsapp.router, tags=["whatsapp"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(records.router, tags=["records"])
app.include_router(accounts.router, tags=["accounts"])
app.include_router(loans.router, tags=["loans"])
app.include_router(reminders.router, tags=["reminders"])
app.include_router(settings_router.router, tags=["settings"])
app.include_router(reports.router, tags=["reports"])
app.include_router(export.router, tags=["export"])


@app.get("/health")
def health():
    return health_summary()
