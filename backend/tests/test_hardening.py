"""Week-1 hardening: the guards that stop duplicate reports, duplicate payouts,
accidental live messaging, and spreadsheet formula injection.

Each test pins a behaviour that used to fail silently in production.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

import app.services.advisory as advisory
import app.services.sms as sms
from app.core.config import Settings
from app.core.csv_export import BOM, safe_cell
from app.db.models import AdvisoryMessage, FieldUser, IncentiveReward, InboundMessage, IrrigationClimateLog, UserRole
from app.services.sms import normalise_phone
from app.services.rainfall import MAX_DAILY_GAUGE_MM, aggregate_gauges


# --- Phone numbers -------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("0788 123 456", "+250788123456"),
    ("0788-123-456", "+250788123456"),
    ("(078) 812-3456", "+250788123456"),
    ("788123456", "+250788123456"),
    ("250788123456", "+250788123456"),
    ("+250 788 123 456", "+250788123456"),
    ("00250788123456", "+250788123456"),
    ("+254 712 345 678", "+254712345678"),
])
def test_one_number_has_one_spelling(raw, expected):
    assert normalise_phone(raw) == expected


def test_invalid_numbers_are_refused():
    assert not sms.is_valid_phone("0788123456")  # not normalised yet
    assert not sms.is_valid_phone("+0123456789")  # no country code can start with zero
    assert sms.is_valid_phone("+250788123456")


# --- Rainfall aggregation -------------------------------------------------------------

def test_rainfall_aggregation_caps_malformed_and_daily_gauge_totals():
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    rows = [("gauge-a", now, 500), ("gauge-a", now + timedelta(hours=1), 100),
            ("gauge-b", now, 25)]
    totals, counts = aggregate_gauges(rows)
    assert totals["gauge-a"] == MAX_DAILY_GAUGE_MM
    assert counts["gauge-a"] == 1  # the second row is capped by the same-day limit
    assert totals["gauge-b"] == 25


# --- Gateway retries -----------------------------------------------------------------

def test_sms_retry_records_one_report_and_sends_one_reply(client, session_factory):
    payload = {"id": "ATXid-retry-1", "from": "+250788000001", "to": "8448", "text": "IMVURA 12"}
    first = client.post("/api/v1/sms/inbound", data=payload).json()
    retry = client.post("/api/v1/sms/inbound", data=payload).json()

    assert first["record_type"] == "irrigation_report" and first["reply_status"] == "dry_run"
    assert retry["reply_status"] == "duplicate" and retry["record_id"] == first["record_id"]
    assert retry["reply"] == first["reply"]

    with session_factory() as session:
        assert len(session.scalars(select(InboundMessage)).all()) == 1
        assert len(session.scalars(select(AdvisoryMessage).where(AdvisoryMessage.purpose == "auto_reply")).all()) == 1


def test_ussd_retry_replays_the_stored_reply(client, session_factory):
    payload = {"sessionId": "retry-hardening", "phoneNumber": "+250788000001", "text": "1*2*1*1*8*8"}
    first = client.post("/api/v1/simulator/ussd", json=payload).json()
    retry = client.post("/api/v1/simulator/ussd", json=payload).json()

    assert retry["reply_status"] == "duplicate"
    assert retry["response"] == first["response"] and retry["record_id"] == first["record_id"]
    with session_factory() as session:
        assert len(session.scalars(select(InboundMessage)).all()) == 1
    assert len(client.get("/api/v1/citizen-reports").json()) == 1


# --- Reward milestones ---------------------------------------------------------------

def test_a_milestone_can_only_be_paid_once(db, monkeypatch):
    monkeypatch.setattr(advisory, "get_settings", lambda: Settings(_env_file=None, incentive_every_n_reports=1, incentive_max_per_day=10))
    user = FieldUser(phone_number="+250788000009")
    db.add(user)
    db.commit()
    db.add(IrrigationClimateLog(reporter_id=user.id, rainfall_mm=4))
    db.commit()

    first = advisory.maybe_reward(db, user)
    db.commit()
    assert first is not None and first.milestone == 1 and first.status == "dry_run"
    # The same report count is presented again (for example by a concurrent request):
    # the unique (field_user_id, milestone) constraint refuses a second payout.
    assert advisory.maybe_reward(db, user) is None
    db.commit()
    assert len(db.scalars(select(IncentiveReward).where(IncentiveReward.field_user_id == user.id)).all()) == 1


def test_daily_reward_cap_stops_a_report_loop(db, monkeypatch):
    monkeypatch.setattr(advisory, "get_settings", lambda: Settings(_env_file=None, incentive_every_n_reports=1, incentive_max_per_day=2))
    user = FieldUser(phone_number="+250788000010")
    db.add(user)
    db.commit()
    paid = []
    for _ in range(3):
        db.add(IrrigationClimateLog(reporter_id=user.id, rainfall_mm=2))
        db.commit()
        paid.append(advisory.maybe_reward(db, user))
        db.commit()
    assert [reward is not None for reward in paid] == [True, True, False]


# --- Consent and opt-out -------------------------------------------------------------

def test_hagarika_opts_out_and_silences_broadcasts(client, district, session_factory):
    from app.services.advisory import sector_recipients
    from app.services.notifications import notify_cell

    before = client.post("/api/v1/sms/inbound", data={"from": "+250788000001", "text": "IMVURA 3"}).json()
    assert before["reply_status"] == "dry_run"

    assert "HAGARIKA" in client.post("/api/v1/sms/inbound", data={"from": "+250788000001", "text": "HAGARIKA"}).json()["reply"]
    with session_factory() as session:
        user = session.scalar(select(FieldUser).where(FieldUser.phone_number == "+250788000001"))
        assert user.opted_out_at is not None and user.consent_at is not None
        assert "+250788000001" not in [phone for phone, _ in sector_recipients(session, district["sector_id"])]
        assert notify_cell(session, district["cell_id"], "Closing the loop", preview=True)["recipients"] == 1

    # A transactional reply to a message the person sends is still delivered.
    opened = client.post("/api/v1/sms/inbound", data={"from": "+250788000001", "text": "IMVURA 4"}).json()
    assert opened["record_type"] == "irrigation_report" and opened["reply_status"] == "dry_run"

    # ONGERA starts broadcasts again.
    client.post("/api/v1/sms/inbound", data={"from": "+250788000001", "text": "ONGERA"})
    with session_factory() as session:
        assert session.scalar(select(FieldUser).where(FieldUser.phone_number == "+250788000001")).opted_out_at is None
        assert "+250788000001" in [phone for phone, _ in sector_recipients(session, district["sector_id"])]


def test_first_message_records_consent(client, session_factory):
    client.post("/api/v1/sms/inbound", data={"from": "+250788000077", "text": "hello"})
    with session_factory() as session:
        user = session.scalar(select(FieldUser).where(FieldUser.phone_number == "+250788000077"))
        assert user.consent_at is not None and user.consent_at.tzinfo is not None


# --- CSV downloads -------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("=HYPERLINK(\"http://evil\")", "'=HYPERLINK(\"http://evil\")"),
    ("+250788123456", "'+250788123456"),
    ("-2", "'-2"),
    ("@SUM(A1)", "'@SUM(A1)"),
    ("\tTabbed", "'\tTabbed"),
    ("Rice", "Rice"),
    (None, ""),
    (12, "12"),
])
def test_csv_cells_cannot_start_a_formula(raw, expected):
    assert safe_cell(raw) == expected


def test_csv_download_starts_with_a_bom_and_neutralises_formulas(auth, client, district):
    farmer_headers = auth("farmer@example.org", role=UserRole.farmer)
    client.post("/api/v1/citizen-reports", json={"cell_id": district["cell_id"], "crop_type": "=cmd|' /C calc'!A0"}, headers=farmer_headers)
    response = client.get("/api/v1/field-reports/export.csv", headers=auth("officer@example.org", role=UserRole.district_officer))
    assert response.status_code == 200
    assert response.content.startswith(BOM.encode("utf-8"))
    assert "'=cmd" in response.text


# --- Runtime guards and headers ------------------------------------------------------

def test_dev_auth_bypass_needs_the_explicit_flag():
    def settings(**values):
        values.setdefault("dev_auth_bypass_enabled", False)
        return Settings(_env_file=None, environment="development", require_api_key=False, **values)

    assert settings().dev_auth_bypass is False
    assert settings(dev_auth_bypass_enabled=True).dev_auth_bypass is True
    assert Settings(_env_file=None, environment="production", require_api_key=True,
                    dev_auth_bypass_enabled=True).dev_auth_bypass is False


def test_production_refuses_the_dev_bypass():
    with pytest.raises(RuntimeError, match="DEV_AUTH_BYPASS"):
        Settings(_env_file=None, environment="production", require_api_key=True, dev_auth_bypass_enabled=True,
                 database_url="postgresql://u:p@db/cs", cookie_secure=True, cors_origins="",
                 gateway_callback_token="t" * 32).guard_runtime()


def test_live_sending_is_refused_outside_production_without_the_flag(monkeypatch):
    staging = Settings(_env_file=None, environment="staging", sms_provider="africas_talking",
                       africas_talking_api_key="live-key", allow_live_messages=False)
    monkeypatch.setattr(sms, "get_settings", lambda: staging)
    assert sms.live("africas_talking") is False
    assert sms.send_sms("+250788123456", "x")["status"] == "dry_run"
    assert sms.send_airtime("+250788123456", 100)["status"] == "dry_run"

    allowed = staging.model_copy(update={"allow_live_messages": True})
    monkeypatch.setattr(sms, "get_settings", lambda: allowed)
    assert sms.live("africas_talking") is True

    production = allowed.model_copy(update={"environment": "production"})
    monkeypatch.setattr(sms, "get_settings", lambda: production)
    assert sms.live("africas_talking") is True


def test_readiness_probe_checks_database(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_responses_carry_a_report_only_csp_and_a_server_request_id(client):
    response = client.get("/health", headers={"X-Request-ID": "chosen-by-the-client"})
    policy = response.headers["Content-Security-Policy-Report-Only"]
    assert "default-src 'self'" in policy and "object-src 'none'" in policy
    assert "frame-ancestors 'none'" in policy
    # The client cannot choose the id that appears in the logs.
    assert response.headers["X-Request-ID"] != "chosen-by-the-client"
