import json
from pathlib import Path

import httpx
import pytest

from app.services.assistant import documents, local_response, retrieve
from app.services.rag.evaluation import evaluate, ranking_metrics, validate_cases


def test_metrics_have_hand_calculated_denominators():
    result = ranking_metrics({"a", "b"}, ["x", "a"], 3)
    assert result["precision_at_k"] == pytest.approx(1 / 3)
    assert result["recall_at_k"] == .5
    assert result["mrr"] == .5
    assert result["ndcg"] == pytest.approx((1 / 1.584962500721156) / (1 + 1 / 1.584962500721156))
    assert ranking_metrics(set(), [], 3)["recall_at_k"] is None
    with pytest.raises(ValueError):
        ranking_metrics({"a"}, ["a", "a"])


def test_evaluation_corpus_is_bounded_diverse_and_network_free(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: pytest.fail("Offline benchmark called provider"))
    path = Path(__file__).resolve().parents[1] / "app/knowledge/evaluation.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    validate_cases(cases, {row["id"] for row in documents()})
    assert len(cases) >= 50
    assert {"en", "rw"} == {row["language"] for row in cases}
    assert {"injection", "unauthorized", "unanswerable", "multi_document", "ambiguous", "paraphrase"} <= {row["category"] for row in cases}
    report = evaluate(cases, retrieve, local_response)
    assert report["provider_calls"] == 0
    assert report["summary"]["cases"] == len(cases)
    assert report["by_language"]["rw"]["cases"] == 8
    assert report["not_measured"]


def test_dataset_validation_rejects_bad_labels_and_unsubstantiated_review():
    case = dict(id="x", question="USSD", relevant_ids=["unknown"], language="en", expected_mode="documents")
    with pytest.raises(ValueError, match="Unknown"):
        validate_cases([case], {"field-ussd"})
    case.update(relevant_ids=[], language="rw", review_status="approved")
    with pytest.raises(ValueError, match="Native"):
        validate_cases([case], set())
    with pytest.raises(ValueError, match="Empty"):
        validate_cases([], set())
