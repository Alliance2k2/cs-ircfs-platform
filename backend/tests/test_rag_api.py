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


def test_source_search_status_reindex_and_safe_lifecycle_audit(auth, client, monkeypatch, session_factory):
    import app.api.routes.assistant as route
    from sqlalchemy import select
    from app.db.models import AuditEvent

    monkeypatch.setattr(route, "get_settings", lambda: Settings(_env_file=None, assistant_ingestion_enabled=True))
    admin = auth("manage-rag@fixture.test", role=UserRole.administrator)
    body = b"Synthetic heliostat maintenance procedure. Check the isolation checklist."
    source = client.post("/api/v1/assistant/documents?filename=x.txt&title=Heliostat", headers=admin, content=body).json()
    base = "/api/v1/assistant/documents"
    listed = client.get(base + "?q=HELIO&status=pending", headers=admin).json()
    assert len(listed) == 1 and listed[0]["chunk_count"] == 1
    assert listed[0]["processing_status"] == "indexed" and listed[0]["embedding_count"] == 0
    assert client.get(base + "?q=%25", headers=admin).json() == []  # Literal wildcard.
    assert client.get(base + "?status=approved", headers=admin).json() == []
    url = f"{base}/{source['version_id']}/reindex"
    assert client.post(url, headers={**admin, "Origin": "https://other.invalid"}).status_code == 403
    assert client.post(url, headers=admin).json()["status"] == "indexed"
    assert client.post(f"{base}/{source['version_id']}/approve", headers=admin, json={"reference": "fixture review"}).status_code == 200
    assert len(client.get(base + "?status=approved", headers=admin).json()) == 1
    assert client.delete(f"{base}/{source['document_id']}", headers=admin).status_code == 200
    with session_factory() as db:
        events = list(db.scalars(select(AuditEvent).where(AuditEvent.action.like("knowledge.%"))))
        assert {event.action for event in events} == {"knowledge.upload", "knowledge.approve", "knowledge.remove", "knowledge.reindex"}
        assert all("heliostat maintenance" not in (event.detail or "") for event in events)


def test_knowledge_config_and_reindex_are_permission_protected(auth, client):
    assert client.get("/api/v1/assistant/config").status_code == 401
    assert client.post("/api/v1/assistant/documents/missing/reindex").status_code == 401
    planner = auth("config-planner@fixture.test", role=UserRole.district_planner)
    config = client.get("/api/v1/assistant/config", headers=planner).json()
    assert config["uploads_enabled"] is False and config["generation_enabled"] is False
    for method, path in [("get", "/documents?q=secret"), ("get", "/documents/missing/preview"), ("post", "/documents/missing/reindex")]:
        assert getattr(client, method)("/api/v1/assistant" + path, headers=planner).status_code == 403


def test_reindex_failure_is_visible_and_retry_keeps_approval_pending(auth, client, monkeypatch):
    import app.api.routes.assistant as route
    import app.services.rag.embeddings as embeddings

    monkeypatch.setattr(route, "get_settings", lambda: Settings(_env_file=None, assistant_ingestion_enabled=True,
                        assistant_embedding_path="synthetic-unavailable", assistant_embedding_revision="fixture-v1"))
    admin = auth("retry-rag@fixture.test", role=UserRole.administrator)
    source = client.post("/api/v1/assistant/documents?filename=x.txt&title=Retry", headers=admin,
                         content=b"Synthetic retry procedure for reviewing an isolation checklist.").json()

    def unavailable(*args):
        raise OSError("private model path")

    monkeypatch.setattr(embeddings, "local_provider", unavailable)
    url = f"/api/v1/assistant/documents/{source['version_id']}/reindex"
    failed = client.post(url, headers=admin)
    assert failed.status_code == 503 and "private model path" not in failed.text
    listed = client.get("/api/v1/assistant/documents", headers=admin).json()[0]
    assert listed["processing_status"] == "failed" and listed["status"] == "pending"
    monkeypatch.setattr(route, "get_settings", lambda: Settings(_env_file=None))
    assert client.post(url, headers=admin).json()["status"] == "indexed"
    listed = client.get("/api/v1/assistant/documents", headers=admin).json()[0]
    assert listed["processing_status"] == "indexed" and listed["status"] == "pending"


def test_http_retrieval_does_not_expose_out_of_sector_sources(auth, client, session_factory, district):
    from sqlalchemy import select
    from app.db.models import PlatformAccount, Sector
    from app.services.rag.store import ingest, approve
    from app.core.security import Principal

    admin = Principal(name="fixture", role=UserRole.administrator, account_id=1)
    with session_factory() as db:
        other = Sector(name="Other fixture sector")
        db.add(other)
        db.flush()
        version, _ = ingest(db, filename="x.txt", data=b"The zephyr valve follows the restricted checklist.", title="Zephyr",
                            roles=["district_planner"], sector_ids=[other.id])
        approve(db, version.id, admin, "fixture approval")
        db.commit()
    planner = auth("scoped-rag@fixture.test", role=UserRole.district_planner)
    with session_factory() as db:
        account = db.scalar(select(PlatformAccount).where(PlatformAccount.email == "scoped-rag@fixture.test"))
        account.sectors = [db.get(Sector, district["sector_id"])]
        db.commit()
    result = client.post("/api/v1/assistant/ask", headers=planner, json={"question": "zephyr valve checklist"}).json()
    assert not any(row.get("document_id") == version.document_id for row in result["sources"])
    assert "restricted checklist" not in result["answer"]
