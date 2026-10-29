from collections import defaultdict
from threading import Lock


_lock = Lock()
_http_statuses: dict[str, int] = defaultdict(int)
_http_paths: dict[str, int] = defaultdict(int)
_http_latency_total_ms: dict[str, float] = defaultdict(float)
_http_requests_total = 0


def record_http_request(method: str, path: str, status: int, duration_ms: float) -> None:
    global _http_requests_total
    route_key = f"{method} {path}"
    with _lock:
        _http_requests_total += 1
        _http_statuses[str(status)] += 1
        _http_paths[route_key] += 1
        _http_latency_total_ms[route_key] += duration_ms


def snapshot() -> dict:
    with _lock:
        return {
            "http_requests_total": _http_requests_total,
            "http_status_total": dict(_http_statuses),
            "http_route_requests_total": dict(_http_paths),
            "http_route_latency_total_ms": dict(_http_latency_total_ms),
        }
