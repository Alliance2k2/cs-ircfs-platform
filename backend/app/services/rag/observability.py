"""Bounded process-local metrics. Never accepts prompts, sources or account IDs."""
import hashlib
import math
from collections import Counter
from threading import Lock

_lock = Lock()
_events = Counter()
_latencies = Counter()
_models = Counter()
EVENTS = frozenset({"documents", "generated", "no_evidence", "privacy_refusal", "total", "retrieval", "retrieval_failure",
                    "generation", "provider_failure", "embedding_failure", "ingestion_indexed", "source_approved", "source_deleted",
                    "feedback_helpful", "feedback_unhelpful", "input_tokens", "output_tokens"})


def record(event, *, duration_ms=None, count=1, model=None):
    if event not in EVENTS or not isinstance(count, int) or not 0 <= count <= 1_000_000_000:
        raise ValueError("Invalid metric event/count")
    if duration_ms is not None and (not math.isfinite(duration_ms) or duration_ms < 0):
        raise ValueError("Invalid metric duration")
    with _lock:
        _events[event] += count
        if duration_ms is not None:
            _latencies[event] += duration_ms
        if model:
            digest = hashlib.sha256(model.encode()).hexdigest()[:12]
            if digest not in _models and len(_models) >= 16:
                digest = "overflow"
            _models[digest] += 1


def snapshot():
    with _lock:
        return {"events": dict(_events), "latency_total_ms": dict(_latencies), "model_revision_counts": dict(_models),
                "estimated_api_cost": None, "scope": "process_local_since_start"}
