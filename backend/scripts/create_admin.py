"""Create or update an administrator account.

Usage:
    python scripts/create_admin.py you@example.org                      # promote, or create (asks for a password)
    python scripts/create_admin.py you@example.org --password 'Secret1!' # set/reset the password without prompting
    python scripts/create_admin.py you@example.org --reset-password     # prompt for a new password on an existing account
    python scripts/create_admin.py you@example.org --role district_planner

Changing a password also signs the account out everywhere (its stored sessions are deleted).
"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make the `app` package importable

from sqlalchemy import delete, select  # noqa: E402

from app.api.routes.auth import hash_password  # noqa: E402
from app.db.models import AuthSession, PlatformAccount, UserRole  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def ask_password(email: str) -> str:
    password = getpass.getpass(f"Password for {email} (8+ characters): ")
    if len(password) < 8 or password != getpass.getpass("Repeat the password: "):
        raise SystemExit("Passwords must match and be at least 8 characters.")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("email")
    parser.add_argument("--role", default="administrator", choices=[role.value for role in UserRole])
    parser.add_argument("--name", default=None, help="Full name for a new account")
    parser.add_argument("--password", default=None, help="Set the password without prompting (new or existing account)")
    parser.add_argument("--reset-password", action="store_true", help="Prompt for a new password on an existing account")
    args = parser.parse_args()

    email = args.email.strip().lower()
    if args.password is not None and len(args.password) < 8:
        raise SystemExit("The password must be at least 8 characters.")

    with SessionLocal() as db:
        account = db.scalar(select(PlatformAccount).where(PlatformAccount.email == email))
        password = args.password or (ask_password(email) if account is None or args.reset_password else None)

        if account is None:
            account = PlatformAccount(email=email, full_name=args.name or email.split("@")[0], password_hash=hash_password(password))
            db.add(account)
            action = "created"
        else:
            action = "updated"
            if password is not None:
                account.password_hash = hash_password(password)
                # A password reset must end every existing session for this account.
                db.execute(delete(AuthSession).where(AuthSession.account_id == account.id))

        account.role = UserRole(args.role)
        account.status = "active"
        db.commit()
        print(f"{email} is now an active {args.role.replace('_', ' ')} ({action}).")
        if password is not None:
            print("Password set. Existing sessions for this account were signed out.")


if __name__ == "__main__":
    main()
