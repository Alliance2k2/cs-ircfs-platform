from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from app.db.models import UserRole
from app.services import assistant


def test_document_lookup_is_local_and_has_reproducible_sources(client, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Local lookup must never contact a provider")
    monkeypatch.setattr(httpx, "AsyncClient", no_network)
    response = client.post("/api/v1/assistant/ask", json={"question": "How do I change the USSD language?"})
    assert response.status_code == 200
    result = response.json()
    assert result["mode"] == "documents"
    assert result["sources"][0]["id"] == "field-ussd"
    assert "option 0" in result["answer"]
    assert len(result["sources"][0]["revision"]) == 12


@pytest.mark.parametrize("question,mode", [("quantum entanglement spectroscopy", "no_evidence"), ("Find +250788111222 rainfall records", "privacy_refusal"), ("Find alice@example.org", "privacy_refusal"), ("USSD sk-fixture-secret-123456789", "privacy_refusal")])
def test_unknown_and_personal_questions_never_call_provider(client, monkeypatch, question, mode):
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: (_ for _ in ()).throw(AssertionError("Should not reach generation")))
    result = client.post("/api/v1/assistant/ask", json={"question": question}).json()
    assert result["mode"] == mode and result["sources"] == []


def test_assistant_requires_staff_permissions(auth, client):
    assert client.post("/api/v1/assistant/ask", json={"question": "USSD language"}).status_code == 401
    monitor = auth("monitor@fixture.test", role=UserRole.citizen_science_monitor)
    assert client.post("/api/v1/assistant/ask", headers=monitor, json={"question": "USSD language"}).status_code == 403
    planner = auth("planner@fixture.test", role=UserRole.district_planner)
    assert client.post("/api/v1/assistant/ask", headers=planner, json={"question": "USSD language"}).status_code == 200


@pytest.mark.parametrize("question", [" ", "x" * 1201])
def test_question_bounds(client, question):
    assert client.post("/api/v1/assistant/ask", json={"question": question}).status_code == 422


@pytest.mark.parametrize("text,status,expected", [("Use main-menu option 0 to change language. [field-ussd]", 200, "generated"), ("Invented facts [invented-source]", 200, "documents"), ("Uncited answer", 200, "documents"), ("provider failure", 503, "documents"), ("Kinyarwanda wording is certified and approved. [field-ussd]", 200, "documents")])
def test_opt_in_generation_and_safe_fallback(client, monkeypatch, text, status, expected):
    monkeypatch.setattr(assistant, "get_settings", lambda: SimpleNamespace(assistant_generation_enabled=True, assistant_openai_api_key=SecretStr("test-only-secret"), assistant_model="fixture-model"))
    actual_client = httpx.AsyncClient
    def provider(request):
        import json
        payload = json.loads(request.content)
        assert payload["store"] is False
        assert "phone_number" not in request.content.decode()
        return httpx.Response(status, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: actual_client(transport=httpx.MockTransport(provider), **kwargs))
    result = client.post("/api/v1/assistant/ask", json={"question": "USSD language"}).json()
    assert result["mode"] == expected
    assert "test-only-secret" not in str(result)
    if expected == "documents":
        assert "notice" in result


def test_corpus_is_only_engineering_procedures():
    docs = assistant.documents()
    assert len({doc["id"] for doc in docs}) == len(docs)
    assert all(doc["reference"].startswith("docs/") for doc in docs)
    assert all(not assistant.PERSONAL.search(doc["text"]) for doc in docs)
