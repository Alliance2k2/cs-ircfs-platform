"""Start a throwaway platform for the browser end-to-end tests (frontend/e2e).

It builds a fresh SQLite database with Alembic, adds the demonstration data and one
account per role, and serves the API and the built React app on 127.0.0.1:8770 with
real sign-in (REQUIRE_API_KEY=true).

Everything that could reach the outside world is switched off here, whatever the
project .env says: SMS and airtime stay in dry-run, the weather forecast and Mapbox are
disabled and the weekly scheduler is off. The script refuses any database other than
the temporary SQLite file it creates, so it can never touch a shared database.

Usage (from backend/):  python scripts/run_e2e_server.py [--port 8770]
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ACCOUNTS = {
    "admin@e2e.test": ("administrator", "E2E Administrator"),
    "planner@e2e.test": ("district_planner", "E2E Planner"),
    "officer@e2e.test": ("district_officer", "E2E Officer"),
    "monitor@e2e.test": ("citizen_science_monitor", "E2E Monitor"),
    "leader@e2e.test": ("cooperative_leader", "E2E Cooperative Leader"),
}
PASSWORD = "e2e-password-2026"  # test-only accounts in a temporary database


def sandbox_environment(database: Path, port: int) -> None:
    """Environment variables override .env, so these always win."""
    os.environ.update({
        "ENVIRONMENT": "staging",
        "DATABASE_URL": f"sqlite:///{database.as_posix()}",
        "REQUIRE_API_KEY": "true",
        "API_KEY_ROLES": "",
        "COOKIE_SECURE": "false",
        "CORS_ORIGINS": f"http://127.0.0.1:{port}",
        "SMS_PROVIDER": "dry_run",
        "AIRTIME_PROVIDER": "dry_run",
        "AFRICAS_TALKING_USERNAME": "",
        "AFRICAS_TALKING_API_KEY": "",
        "GOOGLE_CLIENT_ID": "",
        "ALERT_PHONE_NUMBERS": "",
        "WEATHER_FORECAST_ENABLED": "false",
        "ADVICE_SCHEDULE_ENABLED": "false",
        "MAPBOX_ACCESS_TOKEN": "",
        "GATEWAY_CALLBACK_TOKEN": "e2e-only-gateway-token-not-secret",
    })


def prepare(database: Path) -> None:
    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(config, "head")

    from sqlalchemy import select

    from app.api.routes.auth import hash_password
    from app.db.models import PlatformAccount, UserRole
    from app.db.session import SessionLocal
    from scripts.seed_demo_data import seed

    with SessionLocal() as db:
        if db.bind.dialect.name != "sqlite" or Path(db.bind.url.database).resolve() != database.resolve():
            raise SystemExit("Refusing to seed: the end-to-end server only uses its own temporary SQLite file.")
        print(seed(db))
        for email, (role, name) in ACCOUNTS.items():
            if db.scalar(select(PlatformAccount).where(PlatformAccount.email == email)) is None:
                db.add(PlatformAccount(email=email, full_name=name, role=UserRole(role), status="active", password_hash=hash_password(PASSWORD)))
        db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()
    database = Path(tempfile.mkdtemp(prefix="cs-ircfs-e2e-")) / "e2e.db"
    sandbox_environment(database, args.port)
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    prepare(database)

    import uvicorn

    print(f"End-to-end platform on http://127.0.0.1:{args.port} (database {database})", flush=True)
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
