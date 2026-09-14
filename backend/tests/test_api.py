from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.config import Settings
import app.core.security as security


def test_user_creation_and_reference_validation(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: Settings(_env_file=None, environment="development", require_api_key=False))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    test_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(engine)

    def override_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/users", json={"phone_number": "+250 788 111 222", "full_name": "Test Farmer"})
            assert response.status_code == 201
            user_id = response.json()["id"]
            assert response.json()["phone_number"] == "+250788111222"

            response = client.post("/api/v1/irrigation-schemes", json={"name": "Test Scheme", "hectares_developed": 12.5})
            assert response.status_code == 201
            assert client.post("/api/v1/irrigation-schemes", json={"name": "Test Scheme"}).status_code == 409
            assert any(item["name"] == "Test Scheme" for item in client.get("/api/v1/irrigation-schemes").json())

            response = client.post("/api/v1/feedback", json={"category": "Water access", "message": "The canal is blocked"})
            assert response.status_code == 201

            response = client.post("/api/v1/citizen-reports", json={"reporter_id": user_id, "crop_type": "Maize"})
            assert response.status_code == 201
            assert client.delete(f"/api/v1/users/{user_id}").status_code == 409

            response = client.post("/api/v1/citizen-reports", json={"reporter_id": 9999, "crop_type": "Maize"})
            assert response.status_code == 422

            response = client.post("/api/v1/irrigation-reports", json={"reporter_id": user_id, "infrastructure_name": "Pump A", "operational_status": "offline"})
            assert response.status_code == 201
            queue = client.get("/api/v1/analytics/act-now").json()
            infrastructure = [item for item in queue if item["item_type"] == "infrastructure"]
            assert len(infrastructure) == 1
            case_id = infrastructure[0]["item_id"]
            response = client.patch(f"/api/v1/cases/{case_id}", json={"status": "resolved", "action_taken": "Pump repaired"})
            assert response.status_code == 200
            assert all(item["item_type"] != "infrastructure" for item in client.get("/api/v1/analytics/act-now").json())
            assert len(client.get(f"/api/v1/cases/{case_id}/history").json()) == 1
            assert client.post(f"/api/v1/cases/{case_id}/simulate-notification").status_code == 200
            response = client.post("/api/v1/users", json={"phone_number": "+250788111223", "latitude": -2.05, "longitude": 30.1})
            assert response.status_code == 201
            removable_id = response.json()["id"]
            assert any(feature["feature_type"] == "farmer" for feature in client.get("/api/v1/map-data").json()["features"])
            assert client.delete(f"/api/v1/users/{removable_id}").status_code == 204
            assert all(user["id"] != removable_id for user in client.get("/api/v1/users").json())
            assert client.get("/api/v1/geography/farms").status_code == 501
    finally:
        app.dependency_overrides.clear()


def test_production_requires_authentication_even_if_flag_is_false(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: Settings(_env_file=None, environment="production", require_api_key=False))
    with TestClient(app) as client:
        assert client.get("/api/v1/analytics/act-now").status_code == 401


def test_dashboard_is_served_from_api_origin_and_render_url_uses_psycopg():
    assert Settings(_env_file=None, database_url="postgresql://user:pass@localhost/db").database_url.startswith("postgresql+psycopg://")
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/app.js").status_code == 200
        assert client.get("/health").status_code == 200
