from app.core import metrics
from app.db.models import UserRole


def test_metrics_require_administrator_and_use_route_templates(client, auth):
    client.cookies.clear()
    assert client.get("/metrics").status_code == 401
    headers = auth("monitor-metrics@example.org", role=UserRole.citizen_science_monitor)
    assert client.get("/metrics", headers=headers).status_code == 403
    headers = auth("admin-metrics@example.org", role=UserRole.administrator)
    client.get("/api/v1/irrigation-schemes/987654/not-real", headers=headers)
    response = client.get("/metrics", headers=headers)
    assert response.status_code == 200
    assert not any("987654" in key for key in response.json()["http_route_requests_total"])


def test_route_cardinality_is_bounded(monkeypatch):
    monkeypatch.setattr(metrics, "_http_paths", metrics.defaultdict(int))
    monkeypatch.setattr(metrics, "_http_latency_total_ms", metrics.defaultdict(float))
    for index in range(metrics.MAX_ROUTE_KEYS + 50):
        metrics.record_http_request("GET", f"/unique-{index}", 404, 1)
    data = metrics.snapshot()
    assert len(data["http_route_requests_total"]) <= metrics.MAX_ROUTE_KEYS + 1
    assert data["http_route_requests_total"]["OTHER /overflow"] == 50
