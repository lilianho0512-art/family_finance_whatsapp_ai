"""Promote / demote a user to global superadmin.

Usage:
    python make_superadmin.py <email>            # promote
    python make_superadmin.py <email> --revoke   # demote
    python make_superadmin.py --list             # list all superadmins
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, run_migrations  # noqa: E402
from app.models import User  # noqa: E402


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    # Make sure tables exist before we touch them.
    try:
        run_migrations()
    except Exception:
        pass

    db = SessionLocal()
    try:
        if args[0] == "--list":
            users = db.query(User).filter(User.is_superadmin.is_(True)).all()
            if not users:
                print("(no superadmins)")
            for u in users:
                print(f"#{u.id}\t{u.email}\tfamily={u.family_id}")
            return

        email = args[0].strip().lower()
        revoke = "--revoke" in args[1:]

        u = db.query(User).filter(User.email == email).first()
        if u is None:
            print(f"ERROR: user not found: {email}")
            sys.exit(1)
        u.is_superadmin = not revoke
        db.commit()
        if revoke:
            print(f"OK: {email} (id={u.id}) is no longer a superadmin")
        else:
            print(f"OK: {email} (id={u.id}) is now a superadmin")
            print(f"    Visit /admin in your browser after logging in.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
