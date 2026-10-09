"""Shared test fixtures: in-memory SQLite, a TestClient, seed data, and auth helpers.

Environment variables take precedence over the project .env so the app is imported
against a throwaway database in development mode with no network calls.
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ENVIRONMENT"] = "development"
os.environ["REQUIRE_API_KEY"] = "false"
os.environ["WEATHER_FORECAST_ENABLED"] = "false"
# Tests must never hit a real telecom provider, whatever the local .env says.
os.environ["SMS_PROVIDER"] = "dry_run"
os.environ["AIRTIME_PROVIDER"] = "dry_run"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.ratelimit import limiter
from app.db.base import Base
from app.db.models import Cell, FieldUser, IrrigationScheme, PlatformAccount, Sector, UserRole
from app.db.session import get_db
from app.main import app

# Rate limiting would otherwise trip across a fast test run; it has its own unit test.
limiter.enabled = False


def production_settings() -> Settings:
    """A production configuration with real sign-in enforced (no dev bypass)."""
    return Settings(_env_file=None, environment="production", require_api_key=True, api_key_roles="")


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory):
    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def district(session_factory):
    """One Ngeruka/Gihembe cell, the two schemes, and two registered field users."""
    with session_factory() as session:
        sector = Sector(name="Ngeruka", latitude=-2.35, longitude=30.15)
        session.add(sector)
        session.flush()
        cell = Cell(name="Gihembe", sector_id=sector.id, latitude=-2.34, longitude=30.16)
        session.add(cell)
        session.flush()
        session.add(IrrigationScheme(name="APEFA Solar", sector_id=sector.id, baseline_yield_target_tons=10.0, baseline_source="test"))
        session.add(IrrigationScheme(name="PADAB"))
        session.add(FieldUser(phone_number="+250788000001", full_name="Monitor", cell_id=cell.id))
        session.add(FieldUser(phone_number="+250788000002", full_name="Neighbour", cell_id=cell.id))
        session.commit()
        return {"sector_id": sector.id, "cell_id": cell.id}


@pytest.fixture()
def auth(monkeypatch, client, session_factory):
    """Turn on production auth and return a helper that registers and signs in an account."""
    import app.core.security as security

    monkeypatch.setattr(security, "get_settings", production_settings)

    def make(email="staff@example.org", password="Str0ng!pass", role=UserRole.district_planner):
        client.post("/api/v1/auth/register", json={"email": email, "password": password, "first_name": "A", "surname": "B"})
        with session_factory() as session:
            account = session.scalar(select(PlatformAccount).where(PlatformAccount.email == email))
            account.role = role
            account.status = "active"  # self-registered accounts wait for approval
            session.commit()
        token = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return make
