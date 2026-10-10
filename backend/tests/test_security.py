"""Security and privacy hardening: gateway authentication, the simulator, grievance
anonymity, personal-data masking, the production guard, and response headers."""
import pytest
from sqlalchemy import select

import app.api.routes.channels as channels
import app.services.sms as sms
from app.core.config import Settings
from app.core.privacy import WITHHELD, mask_phone
from app.db.models import AdvisoryMessage, CitizenScienceLog, CommunityFeedback, InboundMessage, UserRole

TOKEN = "t" * 32


def gateway_settings(**values) -> Settings:
    return Settings(_env_file=None, environment="development", require_api_key=False, **values)


def sms_from(client, text, phone="+250788000001", query=""):
    return client.post(f"/api/v1/sms/inbound{query}", data={"from": phone, "to": "8448", "text": text})


# --- Gateway callbacks -------------------------------------------------------------

@pytest.mark.parametrize("query", ["", "?token=wrong"])
def test_callbacks_refuse_requests_without_the_shared_secret(client, district, monkeypatch, query):
    monkeypatch.setattr(channels, "get_settings", lambda: gateway_settings(gateway_callback_token=TOKEN))
    assert sms_from(client, "IMVURA 12", query=query).status_code == 403
    ussd = client.post(f"/api/v1/ussd{query}", data={"sessionId": "g1", "phoneNumber": "+250788000001", "text": ""})
    assert ussd.status_code == 403


def test_callbacks_accept_the_shared_secret(client, district, monkeypatch):
    monkeypatch.setattr(channels, "get_settings", lambda: gateway_settings(gateway_callback_token=TOKEN))
    assert sms_from(client, "IMVURA 12", query=f"?token={TOKEN}").status_code == 200
    ussd = client.post(f"/api/v1/ussd?token={TOKEN}", data={"sessionId": "g2", "phoneNumber": "+250788000001", "text": ""})
    assert ussd.status_code == 200 and ussd.text.startswith("CON")


def test_callbacks_enforce_the_gateway_address_allow_list(client, district, monkeypatch):
    monkeypatch.setattr(channels, "get_settings", lambda: gateway_settings(gateway_allowed_ips="196.201.214.200"))
    assert sms_from(client, "IMVURA 12").status_code == 403  # the test client is not the gateway


def test_one_phone_is_throttled_without_slowing_other_callers(client, district, monkeypatch):
    monkeypatch.setattr(channels, "PHONE_LIMIT_PER_MINUTE", 2)
    assert sms_from(client, "IMVURA 1").status_code == 200
    assert sms_from(client, "IMVURA 2").status_code == 200
    assert sms_from(client, "IMVURA 3").status_code == 429
    assert sms_from(client, "IMVURA 4", phone="+250788000002").status_code == 200


# --- Phone simulator ---------------------------------------------------------------

def test_simulator_requires_sign_in(auth, client, district):
    auth()  # switches the API to real sign-in
    client.cookies.clear()  # signing in left a session cookie behind
    response = client.post("/api/v1/simulator/sms", json={"from": "+250788000001", "text": "IMVURA 12"})
    assert response.status_code == 401


def test_simulator_marks_records_and_never_reaches_a_provider(client, district, session_factory, monkeypatch):
    live = Settings(_env_file=None, sms_provider="africas_talking", airtime_provider="africas_talking")
    monkeypatch.setattr(sms, "get_settings", lambda: live)

    def no_network(*_args, **_kwargs):
        raise AssertionError("the simulator must not call the telecom provider")

    monkeypatch.setattr(sms.httpx, "post", no_network)
    reply = client.post("/api/v1/simulator/sms", json={"from": "+250788000001", "text": "NZANA 5"}).json()
    assert reply["reply_status"] == "dry_run" and reply["record_type"] == "crop_report"
    with session_factory() as session:
        assert session.get(CitizenScienceLog, reply["record_id"]).data_origin == "simulator"
        assert session.scalar(select(InboundMessage).order_by(InboundMessage.id.desc())).data_origin == "simulator"


def test_simulator_reports_stay_out_of_the_public_figures(client, district):
    client.post("/api/v1/simulator/sms", json={"from": "+250788000001", "text": "IMVURA 12"})
    assert client.get("/api/v1/public/overview").json()["reports"] == 0
    sms_from(client, "IMVURA 12")
    assert client.get("/api/v1/public/overview").json()["reports"] == 1


# --- Grievance anonymity -----------------------------------------------------------

def test_sms_grievance_is_logged_without_the_sender(client, district, session_factory):
    reply = sms_from(client, "IKIBAZO amazi ntagera mu murima wacu").json()
    assert reply["record_type"] == "community_feedback"
    with session_factory() as session:
        inbound = session.scalar(select(InboundMessage).order_by(InboundMessage.id.desc()))
        outbound = session.scalar(select(AdvisoryMessage).order_by(AdvisoryMessage.id.desc()))
        feedback = session.scalar(select(CommunityFeedback))
        assert inbound.phone_number == WITHHELD and inbound.record_id is None
        assert outbound.phone_number == WITHHELD
        assert feedback.reporter_id is None


def test_ussd_grievance_withholds_the_phone_for_the_whole_session(client, district, session_factory):
    def dial(text):
        return client.post("/api/v1/ussd", data={"sessionId": "anon", "phoneNumber": "+250788000001", "text": text})

    dial("")
    dial("5")
    dial("5*1")
    assert dial("5*1*Amazi ntagera mu murima").text.startswith("END Murakoze")
    with session_factory() as session:
        rows = list(session.scalars(select(InboundMessage).where(InboundMessage.session_id == "anon")))
        assert len(rows) == 4
        assert {row.phone_number for row in rows} == {WITHHELD}
        assert all(row.record_id is None for row in rows)


# --- Personal data by role ---------------------------------------------------------

def test_monitors_see_masked_numbers_and_no_message_text(auth, client, district):
    sms_from(client, "IMVURA 12")
    monitor = client.get("/api/v1/channels/activity", headers=auth("m@example.org", role=UserRole.citizen_science_monitor)).json()
    assert monitor["personal_data"] is False
    assert monitor["inbound"][0]["phone_number"] == mask_phone("+250788000001")
    assert monitor["inbound"][0]["text"] is None and monitor["outbound"][0]["message"] is None
    planner = client.get("/api/v1/channels/activity", headers=auth("p@example.org", role=UserRole.district_planner)).json()
    assert planner["inbound"][0]["phone_number"] == "+250788000001" and planner["inbound"][0]["text"] == "IMVURA 12"


def test_household_nutrition_records_are_for_district_staff_only(auth, client, district):
    assert client.get("/api/v1/nutrition-surveys", headers=auth("m@example.org", role=UserRole.citizen_science_monitor)).status_code == 403
    assert client.get("/api/v1/nutrition-surveys", headers=auth("o@example.org", role=UserRole.district_officer)).status_code == 200


def test_mask_phone():
    assert mask_phone("+250788123456") == "+250 7•• ••• 456"
    assert mask_phone(WITHHELD) == WITHHELD and mask_phone(None) is None


# --- Production guard and headers --------------------------------------------------

def production(**overrides) -> Settings:
    values = {"environment": "production", "require_api_key": True, "database_url": "postgresql://u:p@db/cs",
              "cookie_secure": True, "cors_origins": "", "gateway_callback_token": TOKEN}
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_a_complete_production_configuration_starts():
    production().guard_runtime()


@pytest.mark.parametrize("overrides, message", [
    ({"require_api_key": False}, "REQUIRE_API_KEY"),
    ({"database_url": "sqlite:///x.db"}, "PostgreSQL"),
    ({"cookie_secure": False}, "COOKIE_SECURE"),
    ({"cors_origins": "http://localhost:5173"}, "CORS"),
    ({"gateway_callback_token": ""}, "GATEWAY_CALLBACK_TOKEN"),
    ({"gateway_callback_token": "short"}, "GATEWAY_CALLBACK_TOKEN"),
])
def test_unsafe_production_configurations_refuse_to_start(overrides, message):
    with pytest.raises(RuntimeError, match=message):
        production(**overrides).guard_runtime()


def test_responses_carry_security_headers(client):
    headers = client.get("/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in headers and "Permissions-Policy" in headers


# --- Map configuration ---------------------------------------------------------------

def test_map_config_returns_only_public_mapbox_tokens(client, monkeypatch):
    import app.api.routes.public as public

    monkeypatch.setattr(public, "get_settings", lambda: Settings(_env_file=None, mapbox_access_token="pk.abc123"))
    assert client.get("/api/v1/public/map-config").json()["mapbox_token"] == "pk.abc123"
    monkeypatch.setattr(public, "get_settings", lambda: Settings(_env_file=None, mapbox_access_token="sk.secret"))
    assert client.get("/api/v1/public/map-config").json()["mapbox_token"] is None
    monkeypatch.setattr(public, "get_settings", lambda: Settings(_env_file=None, mapbox_access_token=""))
    assert client.get("/api/v1/public/map-config").json() == {"mapbox_token": None, "style": "mapbox://styles/mapbox/light-v11"}
