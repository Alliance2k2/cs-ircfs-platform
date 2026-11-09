"""Regressions for the November stabilization security audit. No real secrets or providers."""
import asyncio
import logging
import subprocess
import sys

import pytest
from sqlalchemy.exc import IntegrityError

from app.main import database_error_handler
from app.core.config import Settings


def test_database_error_does_not_log_bound_values_or_driver_detail(caplog):
    marker = "PRIVATE-PARTICIPANT-AND-CREDENTIAL-FIXTURE"
    error = IntegrityError("INSERT INTO participants VALUES (?)", {"phone": marker}, Exception(marker))
    with caplog.at_level(logging.ERROR, logger="app.main"):
        response = asyncio.run(database_error_handler(None, error))
    assert response.status_code == 500
    assert marker not in caplog.text
    assert "INSERT INTO" not in caplog.text
    assert "IntegrityError" in caplog.text


@pytest.mark.parametrize("endpoint", ["/api/v1/ussd", "/api/v1/sms/inbound", "/api/v1/simulator/ussd", "/api/v1/simulator/sms"])
def test_oversized_callback_is_rejected_before_processing(client, endpoint):
    response = client.post(endpoint, content=b"x" * 16_385, headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json()["detail"] == "Callback body exceeds 16384 bytes"


def test_callback_limit_also_covers_chunked_bodies_without_content_length(client):
    response = client.post("/api/v1/simulator/ussd", content=iter([b"x" * 8192, b"x" * 8193]))
    assert response.status_code == 413


@pytest.mark.parametrize("kind", ["sms", "airtime"])
def test_delivery_receipts_stop_reading_as_soon_as_stream_exceeds_limit(kind):
    from fastapi import HTTPException
    from starlette.requests import Request
    from app.api.routes.delivery import receive

    chunks_read = []

    async def next_chunk():
        chunks_read.append(True)
        return {"type": "http.request", "body": b"x" * 8193, "more_body": len(chunks_read) < 3}

    request = Request({"type": "http", "headers": []}, next_chunk)
    with pytest.raises(HTTPException) as error:
        asyncio.run(receive(kind, request, None))
    assert error.value.status_code == 413
    assert len(chunks_read) == 2


@pytest.mark.parametrize("endpoint,key,phone_key", [
    ("/api/v1/ussd", "sessionId", "phoneNumber"),
    ("/api/v1/sms/inbound", "id", "from"),
    ("/api/v1/simulator/ussd", "sessionId", "phoneNumber"),
])
def test_callback_identifier_width_is_validated_before_database_writes(client, endpoint, key, phone_key):
    response = client.post(endpoint, json={key: "x" * 121, phone_key: "+250788000001", "text": ""})
    assert response.status_code == 422
    assert response.json()["detail"] == f"{key} must not exceed 120 characters"


def test_raw_access_logs_are_disabled_in_favor_of_query_free_request_logs():
    result = subprocess.run([sys.executable, "-c",
        "import logging; from app.core.logging import configure_logging; "
        "configure_logging(); logging.getLogger('uvicorn.access').info('GET /?token=private-fixture'); "
        "logging.getLogger('app.main').info('path=/ status=200')"], capture_output=True, text=True, check=True)
    assert "private-fixture" not in result.stdout + result.stderr
    assert "path=/ status=200" in result.stderr


def test_production_refuses_credentialed_wildcard_cors():
    settings = Settings(_env_file=None, environment="production", require_api_key=True, dev_auth_bypass_enabled=False,
        database_url="postgresql://fixture:fixture@localhost/fixture", cookie_secure=True,
        gateway_callback_token="fixture-token-" * 3, cors_origins="*")
    with pytest.raises(RuntimeError, match="wildcard CORS"):
        settings.guard_runtime()
