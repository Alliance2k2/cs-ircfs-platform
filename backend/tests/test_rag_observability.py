import asyncio
from collections import Counter
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from app.services import assistant
from app.services.rag import observability
from app.services.rag.citations import validate, validate_extractive
from app.services.rag.providers import Ollama, OpenAIResponses, token_count
from scripts.evaluate_citation_support import audit


def test_metrics_are_bounded_and_do_not_contain_user_content(monkeypatch):
    monkeypatch.setattr(observability, "_events", Counter())
    monkeypatch.setattr(observability, "_models", Counter())
    monkeypatch.setattr(observability, "_latencies", Counter())
    for index in range(30):
        observability.record("generation", duration_ms=2, model=f"fixture-model-{index}")
    result = observability.snapshot()
    assert result["events"]["generation"] == 30
    assert len(result["model_revision_counts"]) <= 17
    assert "fixture-model" not in str(result)
    assert result["estimated_api_cost"] is None
    with pytest.raises(ValueError):
        observability.record("private prompt")
    with pytest.raises(ValueError):
        observability.record("total", duration_ms=float("nan"))


def test_citations_validate_each_paragraph_but_do_not_claim_entailment():
    sources = [{"id": "fixture"}]
    assert validate("Supported passage [fixture]", sources)
    for answer in ("Unsupported", "Unknown [other]", "Cited [fixture]\n\nUncited factual paragraph"):
        with pytest.raises(ValueError):
            validate(answer, sources)
    report = audit()
    assert report["cases"] == 8
    assert report["unsupported_cases"] == 6
    assert report["unsupported_claim_structural_acceptance_rate"] == 1
    assert report["unsupported_claim_extractive_acceptance_rate"] == 0
    assert report["supported_claim_extractive_acceptance_rate"] == 1
    with pytest.raises(ValueError):
        validate_extractive("Rainfall remains missing, not zero. [fixture]", [{"id": "fixture", "text": "Missing rainfall remains missing, not zero."}])


def test_provider_retry_is_bounded_and_usage_values_cannot_log_secrets(monkeypatch):
    actual_client = httpx.AsyncClient
    calls = []
    def transport(request):
        calls.append(request)
        return httpx.Response(503)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: actual_client(transport=httpx.MockTransport(transport), **kw))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(OpenAIResponses("fixture", "synthetic-key").generate("USSD", []))
    assert len(calls) == 2
    assert token_count("secret") is None and token_count(True) is None
    assert token_count(-1) is None and token_count(12) == 12


def test_ollama_uses_loopback_and_returns_reported_usage(monkeypatch):
    actual_client = httpx.AsyncClient
    def transport(request):
        assert str(request.url) == "http://127.0.0.1:11434/api/chat"
        return httpx.Response(200, json={"done": True, "message": {"content": "Procedure [fixture]"}, "prompt_eval_count": 12, "eval_count": 4})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: actual_client(transport=httpx.MockTransport(transport), **kw))
    result = asyncio.run(Ollama("fixture").generate("USSD", []))
    assert result.text == "Procedure [fixture]" and result.output_tokens == 4


def test_managed_sources_and_unreviewed_language_never_reach_provider(monkeypatch):
    monkeypatch.setattr(assistant, "get_settings", lambda: SimpleNamespace(assistant_generation_enabled=True, assistant_openai_api_key=SecretStr("synthetic-key"), assistant_model="fixture"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: pytest.fail("Generation must be blocked"))
    managed = dict(id="fixture", title="Pump inspection", text="Record pump isolation inspection", revision="abc", reference="knowledge:fixture", document_id="fixture")
    answer = asyncio.run(assistant.respond("pump inspection isolation", additional_sources=[managed]))
    assert answer["mode"] == "documents" and "disabled" in answer["notice"]
    answer = asyncio.run(assistant.respond("USSD language", language="rw"))
    assert answer["mode"] == "documents" and "disabled" in answer["notice"]
