"""Africa's Talking request shape and response handling, without network calls."""
import app.services.sms as sms
from app.core.config import Settings


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


def configure(monkeypatch, username="sandbox", sender=""):
    settings = Settings(_env_file=None, sms_provider="africas_talking", africas_talking_username=username,
                        africas_talking_api_key="test-key", sms_sender_id=sender)
    monkeypatch.setattr(sms, "get_settings", lambda: settings)


def capture(monkeypatch, body):
    calls = []
    monkeypatch.setattr(sms.httpx, "post", lambda url, **kwargs: calls.append((url, kwargs)) or FakeResponse(body))
    return calls


def test_sandbox_uses_sandbox_host_and_omits_unregistered_sender(monkeypatch):
    configure(monkeypatch)
    calls = capture(monkeypatch, {"SMSMessageData": {"Recipients": [{"statusCode": 101, "status": "Success", "messageId": "ATXid_1"}]}})
    result = sms.send_sms("+250788000001", "Murakoze")
    url, kwargs = calls[0]
    assert url == "https://api.sandbox.africastalking.com/version1/messaging"
    assert "from" not in kwargs["data"] and kwargs["headers"]["apiKey"] == "test-key"
    assert result == {"status": "sent", "provider_id": "ATXid_1", "cost": None}


def test_live_username_uses_live_host_with_sender(monkeypatch):
    configure(monkeypatch, username="csircfs", sender="CS-IRCFS")
    calls = capture(monkeypatch, {"SMSMessageData": {"Recipients": [{"statusCode": 101, "status": "Success", "messageId": "x"}]}})
    sms.send_sms("+250788000001", "Murakoze")
    assert calls[0][0] == "https://api.africastalking.com/version1/messaging"
    assert calls[0][1]["data"]["from"] == "CS-IRCFS"


def test_rejected_recipient_is_recorded_as_failed(monkeypatch):
    configure(monkeypatch)
    capture(monkeypatch, {"SMSMessageData": {"Recipients": [{"statusCode": 403, "status": "InvalidPhoneNumber"}]}})
    assert sms.send_sms("+250788000001", "x") == {"status": "failed", "detail": "InvalidPhoneNumber"}
    capture(monkeypatch, {"SMSMessageData": {"Message": "InvalidSenderId", "Recipients": []}})
    assert sms.send_sms("+250788000001", "x")["status"] == "failed"
