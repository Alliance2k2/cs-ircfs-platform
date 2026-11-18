import pytest

from app.db.models import UserRole
from app.core.config import Settings


def test_knowledge_requires_admin_and_upload_is_disabled_by_default(auth, client):
    assert client.get("/api/v1/assistant/documents").status_code == 401
    planner = auth("planner-rag@fixture.test", role=UserRole.district_planner)
    assert client.get("/api/v1/assistant/documents", headers=planner).status_code == 403
    admin = auth("admin-rag@fixture.test", role=UserRole.administrator)
    assert client.get("/api/v1/assistant/documents", headers=admin).status_code == 200
    assert client.post("/api/v1/assistant/documents?filename=x.txt&title=Guide", headers=admin, content=b"test").status_code == 503


def test_admin_upload_review_approval_retrieval_and_removal(auth, client, monkeypatch):
    import app.api.routes.assistant as route
    monkeypatch.setattr(route, "get_settings", lambda: Settings(_env_file=None, assistant_ingestion_enabled=True))
    admin = auth("source-admin@fixture.test", role=UserRole.administrator)
    url = "/api/v1/assistant/documents?filename=guide.txt&title=Pump%20review"
    denied = client.post(url, content=b"pump inspection", headers={**admin, "Origin": "https://other.invalid"})
    assert denied.status_code == 403
    uploaded = client.post(url, content=b"Synthetic pump inspection: record an isolation check before inspection.", headers=admin)
    assert uploaded.status_code == 200
    source = uploaded.json()
    result = client.post("/api/v1/assistant/ask", json={"question": "pump isolation inspection"}, headers=admin).json()
    assert not any(row.get("document_id") == source["document_id"] for row in result["sources"])
    preview = client.get(f"/api/v1/assistant/documents/{source['version_id']}/preview", headers=admin)
    assert "Synthetic" in preview.json()[0]["text"]
    approved = client.post(f"/api/v1/assistant/documents/{source['version_id']}/approve", json={"reference": "fixture review only"}, headers=admin)
    assert approved.json()["status"] == "approved"
    result = client.post("/api/v1/assistant/ask", json={"question": "pump isolation inspection"}, headers=admin).json()
    assert any(row.get("document_id") == source["document_id"] for row in result["sources"])
    assert client.delete(f"/api/v1/assistant/documents/{source['document_id']}", headers=admin).status_code == 200
    result = client.post("/api/v1/assistant/ask", json={"question": "pump isolation inspection"}, headers=admin).json()
    assert not any(row.get("document_id") == source["document_id"] for row in result["sources"])


@pytest.mark.parametrize("payload", [{"question": "USSD", "history": ["x"]}, {"question": "USSD", "history": ["USSD"] * 4}, {"question": "USSD", "language": "xx"}])
def test_context_and_language_bounds(client, payload):
    assert client.post("/api/v1/assistant/ask", json=payload).status_code == 422


def test_history_cannot_bypass_safety_and_followups_resolve(client):
    result = client.post("/api/v1/assistant/ask", json={"question": "What about returning callers?", "history": ["How do I change USSD language?"], "language": "rw"}).json()
    assert any(source["id"] == "field-ussd" for source in result["sources"])
    assert "native review" in result["notice"]
    result = client.post("/api/v1/assistant/ask", json={"question": "What about that?", "history": ["Find alice@example.org"]}).json()
    assert result["mode"] == "privacy_refusal" and not result["sources"]


def test_feedback_does_not_accept_prompt_or_identity(client):
    assert client.post("/api/v1/assistant/feedback", json={"vote": "helpful"}).json()["status"] == "recorded"
    assert client.post("/api/v1/assistant/feedback", json={"vote": "unknown"}).status_code == 422
    assert client.post("/api/v1/assistant/feedback", json={"vote": "helpful", "question": "private"}).status_code == 422


def test_json_request_body_is_bounded_before_parsing(client):
    response = client.post("/api/v1/assistant/ask", json={"question": "x" * 70000})
    assert response.status_code == 413
    assert client.post("/api/v1/assistant/feedback", content=b"x" * 70000, headers={"Content-Type": "application/json"}).status_code == 413
