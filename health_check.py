"""Pre-flight check: ensure folders, .env, and DB are in place."""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

REQUIRED_DIRS = ["data", "uploads", "output", "logs"]
for d in REQUIRED_DIRS:
    p = BASE / d
    p.mkdir(parents=True, exist_ok=True)
print("[health_check] folders OK")

env_file = BASE / ".env"
if not env_file.exists():
    sample = BASE / ".env.example"
    if sample.exists():
        env_file.write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")
        print("[health_check] .env created from .env.example — please fill in WhatsApp credentials")
    else:
        print("[health_check] WARNING: .env not found and no .env.example available")

try:
    from app.database import run_migrations, init_db
    if run_migrations():
        print("[health_check] alembic migrations applied")
    else:
        init_db()
        print("[health_check] alembic unavailable, used create_all() fallback")
except Exception as e:
    print(f"[health_check] migrations failed ({e}); falling back to create_all()")
    try:
        from app.database import init_db
        init_db()
        print("[health_check] database OK (create_all fallback)")
    except Exception as e2:
        print(f"[health_check] database FAILED: {e2}")
        sys.exit(1)

try:
    from app.services.self_healing_service import health_summary
    summary = health_summary()
    print(f"[health_check] credentials: ok={summary['ok']}")
    for issue in summary.get("issues", []):
        print(f"  ! {issue}")
except Exception as e:
    print(f"[health_check] summary FAILED: {e}")

print("[health_check] DONE")
