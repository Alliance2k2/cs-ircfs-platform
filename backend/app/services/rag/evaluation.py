"""Deterministic offline evaluation: engineering labels, no model calls/judges."""
import hashlib
import math
import statistics
import time
from app.services.rag.citations import validate_extractive


def validate_cases(cases, document_ids):
    seen = set()
    for case in cases:
        if case["id"] in seen or not case["question"].strip():
            raise ValueError("Duplicate case ID or empty question")
        seen.add(case["id"])
        if not set(case["relevant_ids"]) <= document_ids:
            raise ValueError("Unknown relevance label")
        if case["language"] == "rw" and case["review_status"] != "pending_native_review":
            raise ValueError("Native approval must not be inferred by this benchmark")
        if case["expected_mode"] not in {"documents", "no_evidence", "privacy_refusal"}:
            raise ValueError("Unsupported expected mode")
    if not cases:
        raise ValueError("Empty evaluation dataset")


def ranking_metrics(relevant, retrieved, k=3):
    if k < 1 or len(retrieved) != len(set(retrieved)):
        raise ValueError("Positive k and unique retrieved IDs required")
    relevant = set(relevant)
    hits = [int(identifier in relevant) for identifier in retrieved[:k]]
    dcg = sum(hit / math.log2(rank + 2) for rank, hit in enumerate(hits))
    ideal = sum(1 / math.log2(rank + 2) for rank in range(min(k, len(relevant))))
    return {"precision_at_k": sum(hits) / k,
            "recall_at_k": sum(hits) / len(relevant) if relevant else None,
            "mrr": next((1 / (rank + 1) for rank, hit in enumerate(hits) if hit), 0.0),
            "ndcg": dcg / ideal if ideal else None}


def evaluate(cases, retrieve, local_response, k=3):
    rows = []
    for case in cases:
        start = time.perf_counter()
        sources = retrieve(case["question"])[:k]
        result = local_response(case["question"])
        citation_valid = None
        if result["mode"] == "documents":
            try:
                citation_valid = validate_extractive(result["answer"], result["sources"])
            except ValueError:
                citation_valid = False
        latency = (time.perf_counter() - start) * 1000
        ids = [source["id"] for source in sources]
        rows.append({"id": case["id"], "language": case["language"], "category": case["category"],
                     "split": case.get("split", "development"),
                     "expected_mode": case["expected_mode"], "actual_mode": result["mode"],
                     "extractive_citation_valid": citation_valid, "answer_words": len(result["answer"].split()),
                     "relevant_ids": case["relevant_ids"], "retrieved_ids": ids,
                     "mode_correct": case["expected_mode"] == result["mode"], "latency_ms": round(latency, 3),
                     **ranking_metrics(case["relevant_ids"], ids, k)})
    def aggregate(subset):
        answerable = [row for row in subset if row["relevant_ids"]]
        negative = [row for row in subset if row["expected_mode"] != "documents"]
        quoted = [row for row in subset if row["extractive_citation_valid"] is not None]
        return {"cases": len(subset), "answerable_cases": len(answerable),
                **{metric: statistics.mean(row[metric] for row in answerable) if answerable else None
                   for metric in ("precision_at_k", "recall_at_k", "mrr", "ndcg")},
                "mode_accuracy": statistics.mean(row["mode_correct"] for row in subset),
                "abstention_accuracy": statistics.mean(row["mode_correct"] for row in negative) if negative else None,
                "extractive_citation_accuracy": statistics.mean(row["extractive_citation_valid"] for row in quoted) if quoted else None,
                "answer_words_p50": statistics.median(row["answer_words"] for row in subset),
                "answer_words_max": max(row["answer_words"] for row in subset),
                "latency_ms_p50": statistics.median(row["latency_ms"] for row in subset),
                "latency_ms_max": max(row["latency_ms"] for row in subset)}
    return {"k": k, "summary": aggregate(rows),
            "by_language": {language: aggregate([r for r in rows if r["language"] == language])
                            for language in sorted({row["language"] for row in rows})},
            "by_split": {split: aggregate([r for r in rows if r["split"] == split]) for split in sorted({row["split"] for row in rows})},
            "not_measured": ["semantic answer relevance", "claim faithfulness", "hallucination rate", "generated citation entailment"],
            "provider_calls": 0, "provider_tokens": 0, "api_cost": 0,
            "notes": "Latency includes two local retrieval calls per case; cold-cache first case is included. No generation evaluated.",
            "rows": rows}


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()
