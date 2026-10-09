"""Sign-in, session cookies, roles, and account administration."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import AuthSession, PlatformAccount, UserRole


def register(client, email="x@example.org", password="Str0ng!pass"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password, "first_name": "A", "surname": "B"})


def activate(session_factory, email="x@example.org"):
    with session_factory() as session:
        session.scalar(select(PlatformAccount).where(PlatformAccount.email == email)).status = "active"
        session.commit()


def test_register_always_creates_citizen_science_monitor(client):
    response = register(client)
    assert response.status_code == 201
    assert response.json()["role"] == "citizen_science_monitor"


def test_registered_account_waits_for_approval(client, session_factory):
    assert register(client).json()["status"] == "pending"
    refused = client.post("/api/v1/auth/login", json={"email": "x@example.org", "password": "Str0ng!pass"})
    assert refused.status_code == 403
    assert "approval" in refused.json()["detail"]
    assert "set-cookie" not in refused.headers
    activate(session_factory)
    assert client.post("/api/v1/auth/login", json={"email": "x@example.org", "password": "Str0ng!pass"}).status_code == 200


def test_pending_status_is_not_revealed_without_the_password(client):
    register(client)
    response = client.post("/api/v1/auth/login", json={"email": "x@example.org", "password": "wrong-password"})
    assert response.status_code == 401
    assert "approval" not in response.json()["detail"]


def test_login_returns_token_and_sets_httponly_cookie(client, session_factory):
    register(client)
    activate(session_factory)
    response = client.post("/api/v1/auth/login", json={"email": "x@example.org", "password": "Str0ng!pass"})
    assert response.status_code == 200
    assert response.json()["access_token"]
    cookie = response.headers["set-cookie"]
    assert "cs_ircfs_session=" in cookie and "HttpOnly" in cookie


def test_expired_session_returns_401(auth, client, session_factory):
    headers = auth()
    with session_factory() as session:
        record = session.scalar(select(AuthSession))
        record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        session.commit()
    assert client.get("/api/v1/map-data", headers=headers).status_code == 401


def test_suspended_account_returns_403(auth, client, session_factory):
    headers = auth()
    with session_factory() as session:
        account = session.scalar(select(PlatformAccount).where(PlatformAccount.email == "staff@example.org"))
        account.status = "suspended"
        session.commit()
    assert client.get("/api/v1/map-data", headers=headers).status_code == 403


def test_citizen_science_monitor_cannot_reach_planner_endpoints(auth, client):
    headers = auth(role=UserRole.citizen_science_monitor)
    assert client.get("/api/v1/analytics/dashboard-summary", headers=headers).status_code == 200
    assert client.get("/api/v1/analytics/act-now", headers=headers).status_code == 403


def test_admin_can_update_role_and_area_sectors(auth, client, district):
    headers = auth(role=UserRole.administrator)
    register(client, email="officer@example.org")

    # Promote the second account through the admin endpoint.
    accounts = client.get("/api/v1/auth/accounts", headers=headers).json()
    officer_id = next(a["id"] for a in accounts if a["email"] == "officer@example.org")
    response = client.patch(
        f"/api/v1/auth/accounts/{officer_id}",
        headers=headers,
        json={"role": "district_officer", "sector_ids": [district["sector_id"]]},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "district_officer"
    assert response.json()["sector_ids"] == [district["sector_id"]]
    assert client.patch(f"/api/v1/auth/accounts/{officer_id}", headers=headers, json={"sector_ids": [999]}).status_code == 422
