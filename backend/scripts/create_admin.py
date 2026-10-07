"""Create the first administrator account, or promote an existing account.

Usage:
    python scripts/create_admin.py you@example.org            # promote, or create (asks for a password)
    python scripts/create_admin.py you@example.org --role district_planner
"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make the `app` package importable

from sqlalchemy import select  # noqa: E402

from app.api.routes.auth import hash_password  # noqa: E402
from app.db.models import PlatformAccount, UserRole  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("email")
    parser.add_argument("--role", default="administrator", choices=[role.value for role in UserRole])
    parser.add_argument("--name", default=None, help="Full name for a new account")
    args = parser.parse_args()
    email = args.email.strip().lower()
    with SessionLocal() as db:
        account = db.scalar(select(PlatformAccount).where(PlatformAccount.email == email))
        if account is None:
            password = getpass.getpass("Password for the new account (8+ characters): ")
            if len(password) < 8 or password != getpass.getpass("Repeat the password: "):
                raise SystemExit("Passwords must match and be at least 8 characters.")
            account = PlatformAccount(email=email, full_name=args.name or email.split("@")[0], password_hash=hash_password(password))
            db.add(account)
        account.role = UserRole(args.role)
        account.status = "active"
        db.commit()
        print(f"{email} is now an active {args.role.replace('_', ' ')}.")


if __name__ == "__main__":
    main()
