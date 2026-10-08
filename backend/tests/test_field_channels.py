"""USSD, SMS keywords, closing-the-loop, analytics, incentives, and session sign-in."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.security as security
from app.core.config import Settings
from app.db.base import Base
from app.db.models import Cell, IrrigationScheme, Sector, User
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client_and_db(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: Settings(_env_file=None, environment="development", require_api_key=False))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(engine)
    with Session() as db:
        sector = Sector(name="Ngeruka", latitude=-2.35, longitude=30.15)
        db.add(sector); db.flush()
        cell = Cell(name="Gihembe", sector_id=sector.id, latitude=-2.34, longitude=30.16)
        db.add(cell); db.flush()
        db.add(IrrigationScheme(name="APEFA Solar", sector_id=sector.id, baseline_yield_target_tons=10.0, baseline_source="test"))
        db.add(IrrigationScheme(name="PADAB"))
        db.add(User(phone_number="+250788000001", full_name="Monitor", cell_id=cell.id))
        db.add(User(phone_number="+250788000002", full_name="Neighbour", cell_id=cell.id))
        db.commit()

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            yield client, Session
    finally:
        app.dependency_overrides.clear()


def dial(client, text, phone="+250788000001"):
    """Send a USSD step the way Africa's Talking does (form-encoded)."""
    return client.post("/api/v1/ussd", data={"sessionId": "s1", "serviceCode": "*801#", "phoneNumber": phone, "text": text})


def test_ussd_menu_is_kinyarwanda_and_plain_text(client_and_db):
    client, _ = client_and_db
    response = dial(client, "")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text.startswith("CON Kaze kuri CS-IRCFS")
    assert dial(client, "9").text.startswith("END ")


def test_ussd_severe_pest_creates_act_now_case_and_scheme_link(client_and_db):
    client, _ = client_and_db
    assert dial(client, "2*2").text.startswith("CON ")
    final = client.post("/api/v1/ussd?explain=true", json={"phoneNumber": "+250788000001", "text": "2*2*1*5"}).json()
    assert final["response"].startswith("END Murakoze")
    assert final["record_type"] == "crop_report"
    report = client.get("/api/v1/citizen-reports").json()[0]
    assert report["pest_or_disease"] == "Fall armyworm" and report["severity"] == 5 and report["scheme_id"] is not None
    queue = client.get("/api/v1/analytics/act-now").json()
    assert any(item["priority"] == "critical" and "Fall armyworm" in item["title"] for item in queue)


def test_ussd_infrastructure_fault_records_bottleneck(client_and_db):
    client, _ = client_and_db
    assert "Impamvu" in dial(client, "4*1*3").text
    assert dial(client, "4*1*3*1").text.startswith("END ")
    report = client.get("/api/v1/irrigation-reports").json()[0]
    assert report["infrastructure_name"] == "PADAB Pumping Station 1"
    assert report["operational_status"] == "offline" and report["bottleneck_category"] == "technical"


def test_every_third_rainfall_report_earns_airtime(client_and_db):
    client, _ = client_and_db
    replies = [dial(client, f"3*{mm}").text for mm in (2, 3, 4)]
    assert "RWF" not in replies[0] and "RWF" in replies[2]
    rewards = client.get("/api/v1/incentives").json()
    assert len(rewards) == 1 and rewards[0]["amount_rwf"] == 100 and rewards[0]["status"] == "dry_run"
    schedule = {row["sector"]: row for row in client.get("/api/v1/advisory/irrigation-schedule").json()}
    assert schedule["Ngeruka"]["level"] == "irrigate_more"  # 9 mm in 7 days is a dry spell
    preview = client.post("/api/v1/advisory/irrigation-schedule/send", json={"preview": True}).json()
    assert preview["total_recipients"] == 2


def test_new_caller_is_registered_and_grievance_is_anonymous(client_and_db):
    client, _ = client_and_db
    new = "0788 999 111"
    assert "Hitamo umurenge" in dial(client, "", phone=new).text
    assert any(user["phone_number"] == "+250788999111" and user["cell_id"] is None for user in client.get("/api/v1/users").json())
    assert "Gihembe" in dial(client, "1", phone=new).text
    assert dial(client, "1*1", phone=new).text.startswith("END Murakoze! Aho utuye habitswe: Gihembe, Ngeruka")
    assert next(u for u in client.get("/api/v1/users").json() if u["phone_number"] == "+250788999111")["cell_id"] is not None
    # Next session goes straight to the main menu, and the grievance is tied to the caller's cell.
    assert dial(client, "", phone=new).text.startswith("CON Kaze kuri CS-IRCFS")
    assert dial(client, "5*2*The water fee doubled this season", phone=new).text.startswith("END Murakoze")
    feedback = client.get("/api/v1/feedback").json()[0]
    assert feedback["category"] == "Water Pricing" and feedback["reporter_id"] is None


def test_ussd_nutrition_survey_scores_risk(client_and_db):
    client, _ = client_and_db
    dial(client, "6*1*2*2")
    survey = client.get("/api/v1/nutrition-surveys").json()[0]
    assert survey["stunting_risk_score"] == 5
    assert client.get("/api/v1/analytics/nutrition-summary").json()["high_risk_households"] == 1


def test_sms_keywords(client_and_db):
    client, _ = client_and_db
    reply = client.post("/api/v1/sms/inbound", data={"from": "+250788000001", "to": "8448", "text": "Ngeruka Nzana 4"}).json()
    assert reply["record_type"] == "crop_report" and "Nzana" in reply["reply"]
    assert client.post("/api/v1/sms/inbound", data={"from": "+250788000001", "text": "IMVURA 15"}).json()["record_type"] == "irrigation_report"
    assert client.post("/api/v1/sms/inbound", data={"from": "+250788000001", "text": "Ngeruka IKIBAZO Canal gate is broken"}).json()["record_type"] == "community_feedback"
    assert client.get("/api/v1/feedback").json()[0]["message"] == "Canal gate is broken"
    assert "*801#" in client.post("/api/v1/sms/inbound", data={"from": "+250788000001", "text": "hello"}).json()["reply"]
    assert client.get("/api/v1/analytics/pest-heatmap").json()[0]["severity"] == 4
    activity = client.get("/api/v1/channels/activity").json()
    assert len(activity["inbound"]) == 4 and activity["outbound"][0]["purpose"] == "auto_reply"


def test_closing_the_loop_sms_reaches_the_cell(client_and_db):
    client, _ = client_and_db
    dial(client, "5*1*Fertiliser arrived late")
    feedback_id = client.get("/api/v1/feedback").json()[0]["id"]
    assert client.post(f"/api/v1/feedback/{feedback_id}/notify-cell", json={}).status_code == 422
    client.patch(f"/api/v1/feedback/{feedback_id}", json={"status": "resolved", "action_taken": "Delivery rescheduled"})
    preview = client.post(f"/api/v1/feedback/{feedback_id}/notify-cell", json={"preview": True}).json()
    assert preview["recipients"] == 2 and preview["sent"] == 0 and "Delivery rescheduled" in preview["message"]
    assert client.post(f"/api/v1/feedback/{feedback_id}/notify-cell", json={}).json()["sent"] == 2
    health = client.get("/api/v1/analytics/response-health").json()
    assert health["feedback_resolved"] == 1 and health["close_loop_messages"] == 2


def test_scheme_performance_compares_reports_with_target(client_and_db):
    client, _ = client_and_db
    dial(client, "1*2*8")
    performance = {row["name"]: row for row in client.get("/api/v1/analytics/scheme-performance").json()}
    assert performance["APEFA Solar"]["achievement_percent"] == 80.0
    assert performance["APEFA Solar"]["status"] == "watch" and performance["APEFA Solar"]["basis"] == "forecast"
    assert performance["PADAB"]["status"] == "no_target"
    for _ in range(3):
        dial(client, "4*1*2*1")
    padab = {row["name"]: row for row in client.get("/api/v1/analytics/scheme-performance").json()}["PADAB"]
    assert padab["flagged_bottlenecks"] == ["technical"]


def test_registration_cannot_choose_role_and_sessions_authorise(monkeypatch, client_and_db):
    client, _ = client_and_db
    response = client.post("/api/v1/auth/register", json={"email": "x@example.org", "password": "Str0ng!pass", "first_name": "A", "surname": "B", "role": "administrator"})
    assert response.status_code == 201 and response.json()["role"] == "citizen_science_monitor"
    token = client.post("/api/v1/auth/login", json={"email": "x@example.org", "password": "Str0ng!pass"}).json()["access_token"]
    production = Settings(_env_file=None, environment="production", require_api_key=True, api_key_roles="")
    monkeypatch.setattr(security, "get_settings", lambda: production)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/auth/me", headers=headers).json()["role"] == "citizen_science_monitor"
    assert client.get("/api/v1/map-data", headers=headers).status_code == 200
    assert client.get("/api/v1/analytics/act-now", headers=headers).status_code == 403
    assert client.get("/api/v1/analytics/act-now").status_code == 401
    client.post("/api/v1/auth/logout", headers=headers)
    assert client.get("/api/v1/map-data", headers=headers).status_code == 401


def test_monitor_reads_live_figures_but_cannot_act(monkeypatch, client_and_db):
    client, _ = client_and_db
    client.post("/api/v1/auth/register", json={"email": "m@example.org", "password": "Str0ng!pass", "first_name": "M", "surname": "O"})
    token = client.post("/api/v1/auth/login", json={"email": "m@example.org", "password": "Str0ng!pass"}).json()["access_token"]
    monkeypatch.setattr(security, "get_settings", lambda: Settings(_env_file=None, environment="production", require_api_key=True, api_key_roles=""))
    headers = {"Authorization": f"Bearer {token}"}
    for path in ("analytics/dashboard-summary", "analytics/scheme-performance", "analytics/response-health", "analytics/rainfall-map",
                 "analytics/pest-heatmap", "analytics/nutrition-summary", "advisory/irrigation-schedule", "channels/activity"):
        assert client.get(f"/api/v1/{path}", headers=headers).status_code == 200, path
    assert client.get("/api/v1/analytics/act-now", headers=headers).status_code == 403
    assert client.post("/api/v1/advisory/irrigation-schedule/send", headers=headers, json={"preview": True}).status_code == 403
    assert client.get("/api/v1/analytics/dashboard-summary").status_code == 401


def test_public_overview_needs_no_sign_in_and_hides_people(monkeypatch, client_and_db):
    client, _ = client_and_db
    dial(client, "3*12")  # a rain-gauge reading from the Ngeruka monitor
    monkeypatch.setattr(security, "get_settings", lambda: Settings(_env_file=None, environment="production", require_api_key=True, api_key_roles=""))
    response = client.get("/api/v1/public/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["reports"] >= 1 and data["sectors_reporting"] == 1 and data["sectors_total"] == 1
    assert data["recent"][0]["sector"] == "Ngeruka"
    assert data["sectors"][0]["name"] == "Ngeruka" and data["sectors"][0]["reports_30d"] == 1 and data["sectors"][0]["rainfall_mm_7d"] == 12
    assert "+2507" not in response.text and "Monitor" not in response.text


def test_first_call_location_pages_through_sectors(client_and_db):
    client, Session = client_and_db
    with Session() as db:
        for name in ("Gashora", "Juru", "Kamabuye", "Mareba", "Mayange", "Musenyi", "Mwogo", "Nyamata", "Rilima"):
            sector = Sector(name=name)
            db.add(sector); db.flush()
            db.add(Cell(name=f"{name} Cell", sector_id=sector.id))
        db.commit()
    phone = "+250788777666"
    first = dial(client, "", phone=phone).text
    assert "8. Ngeruka" in first and "9. Indi mirenge" in first and "Rilima" not in first
    second = dial(client, "9", phone=phone).text
    assert second.startswith("CON Hitamo umurenge") and "1. Nyamata" in second and "2. Rilima" in second
    assert "Rilima Cell" in dial(client, "9*2", phone=phone).text
    assert dial(client, "9*7", phone=phone).text.startswith("END Igisubizo ntikemewe")
    assert dial(client, "9*2*1", phone=phone).text.startswith("END Murakoze! Aho utuye habitswe: Rilima Cell, Rilima")


def test_retried_sms_is_not_recorded_twice(client_and_db):
    client, _ = client_and_db
    message = {"from": "+250788000001", "to": "8448", "text": "IMVURA 15", "id": "ATXid_abc123"}
    first = client.post("/api/v1/sms/inbound", data=message).json()
    retry = client.post("/api/v1/sms/inbound", data=message).json()
    assert retry["reply_status"] == "duplicate" and retry["record_id"] == first["record_id"]
    assert len(client.get("/api/v1/irrigation-reports").json()) == 1
    assert len(client.get("/api/v1/advisory/messages").json()) == 1
    assert client.post("/api/v1/sms/inbound", data={**message, "id": "ATXid_other"}).json()["record_id"] != first["record_id"]


def test_urgent_case_alerts_staff_by_sms(monkeypatch, client_and_db):
    client, _ = client_and_db
    settings = Settings(_env_file=None, environment="development", require_api_key=False, alert_phone_numbers="0788 111 222, +250788111222, bad")
    monkeypatch.setattr("app.services.notifications.get_settings", lambda: settings)
    dial(client, "2*2*1*4")  # severity 4: high, below the default "critical" threshold
    assert not [m for m in client.get("/api/v1/advisory/messages").json() if m["purpose"] == "staff_alert"]
    dial(client, "2*2*1*5")  # severity 5: critical
    alerts = [m for m in client.get("/api/v1/advisory/messages").json() if m["purpose"] == "staff_alert"]
    assert len(alerts) == 1 and alerts[0]["phone_number"] == "+250788111222"
    assert alerts[0]["message"].startswith("CS-IRCFS CRITICAL: Fall armyworm on Maize, severity 5 (Ngeruka / Gihembe). Case #")


def test_forecast_adds_look_ahead_to_irrigation_advice(monkeypatch, client_and_db):
    client, _ = client_and_db
    import app.services.advisory as advisory
    dial(client, "3*2")  # 2 mm this week in Ngeruka: dry, so irrigate more
    monkeypatch.setattr(advisory, "rainfall_forecast", lambda points: {sector_id: 35.0 for sector_id in points})
    row = client.get("/api/v1/advisory/irrigation-schedule").json()[0]
    assert row["level"] == "normal" and row["forecast_mm_7d"] == 35.0
    assert row["message_en"] == "Rainfall was low (2.0 mm in 7 days), but 35.0 mm is forecast for the next 7 days. Keep the usual schedule and check again in 2-3 days."
    monkeypatch.setattr(advisory, "rainfall_forecast", lambda points: {sector_id: 0.0 for sector_id in points})
    assert client.get("/api/v1/advisory/irrigation-schedule").json()[0]["level"] == "irrigate_more"
    monkeypatch.setattr(advisory, "rainfall_forecast", lambda points: {})  # forecast service down: gauges only
    assert client.get("/api/v1/advisory/irrigation-schedule").json()[0]["message_en"].endswith("this week.")


def test_monthly_report_counts_this_month_only(client_and_db):
    client, _ = client_and_db
    dial(client, "2*2*1*5")      # critical pest report -> case
    dial(client, "3*12")         # rain gauge
    dial(client, "5*2*Fees went up")
    dial(client, "6*1*2*2")      # nutrition survey, high risk
    report = client.get("/api/v1/analytics/monthly-report").json()
    figures = report["figures"]
    assert figures["reports"]["value"] == 2 and figures["reports"]["previous"] == 0 and figures["reports"]["change_percent"] is None
    assert figures["pest_reports"]["value"] == 1 and figures["grievances"]["value"] == 1 and figures["nutrition_surveys"]["value"] == 1
    assert report["cases"]["opened"] == 1 and report["cases"]["by_priority"] == {"critical": 1} and report["cases"]["open_at_month_end"] == 1
    assert report["pests"][0] == {"pest": "Fall armyworm", "reports": 1, "severe": 1, "sectors": ["Ngeruka"]}
    assert report["rainfall"] == [{"sector": "Ngeruka", "rainfall_mm": 12.0, "gauges": 1, "readings": 1}]
    assert report["nutrition"]["high_risk_households"] == 1 and report["sectors_reporting"] == 1
    assert "+2507" not in str(report) and "Fees went up" not in str(report)
    old = client.get("/api/v1/analytics/monthly-report?month=2020-01").json()
    assert old["label"] == "January 2020" and old["previous_month"] == "2019-12" and old["figures"]["reports"]["value"] == 0
    assert client.get("/api/v1/analytics/monthly-report?month=2026-13").status_code == 422
