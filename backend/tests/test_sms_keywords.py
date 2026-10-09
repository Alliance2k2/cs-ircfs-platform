"""Inbound SMS keywords: IMVURA, NZANA, UMUSARURO, IKIBAZO, and help."""


def send(client, text, phone="+250788000001"):
    return client.post("/api/v1/sms/inbound", data={"from": phone, "to": "8448", "text": text}).json()


def test_imvura_creates_rainfall_reading(client):
    reply = send(client, "IMVURA 12.5")
    assert reply["record_type"] == "irrigation_report"
    assert client.get("/api/v1/irrigation-reports").json()[0]["rainfall_mm"] == 12.5


def test_nzana_creates_pest_report(client):
    reply = send(client, "Nzana 4")
    assert reply["record_type"] == "crop_report"
    report = client.get("/api/v1/citizen-reports").json()[0]
    assert report["pest_or_disease"] == "Fall armyworm" and report["severity"] == 4


def test_umusaruro_creates_harvest_report(client):
    reply = send(client, "UMUSARURO IBIGORI 2.5")
    assert reply["record_type"] == "crop_report"
    report = client.get("/api/v1/citizen-reports").json()[0]
    assert report["crop_type"] == "Maize" and report["expected_harvest_tons"] == 2.5
    # The old two-word form records no yield-forecaster extras.
    assert report["crop_variety"] is None and report["expected_harvest_month"] is None


def test_umusaruro_with_variety_and_harvest_month(client):
    reply = send(client, "UMUSARURO IBIGORI 2.5 IBUZI IBYATUNGANYE UKWEZI 3")
    assert reply["record_type"] == "crop_report" and "ibyiciro Ibyatunganye" in reply["reply"]
    report = client.get("/api/v1/citizen-reports").json()[0]
    from datetime import date

    from app.services.reporting import add_months

    assert report["crop_variety"] == "Improved seed"
    assert report["expected_harvest_month"] == add_months(date.today(), 3).isoformat()


def test_umusaruro_planted_months_ago(client):
    reply = send(client, "UMUSARURO IBIGORI 4 IMBERE 2")
    assert reply["record_type"] == "crop_report"
    report = client.get("/api/v1/citizen-reports").json()[0]
    assert report["planting_date"].endswith("-01") and report["expected_harvest_tons"] == 4


def test_umusaruro_still_requires_crop_and_tons(client):
    assert "UMUSARURO <igihingwa>" in send(client, "UMUSARURO IBIGORI")["reply"]
    assert "UMUSARURO <igihingwa>" in send(client, "UMUSARURO 2.5")["reply"]


def test_ikibazo_creates_anonymous_grievance(client, session_factory):
    from sqlalchemy import select

    from app.db.models import CommunityFeedback

    reply = send(client, "IKIBAZO Canal gate is broken")
    assert reply["record_type"] == "community_feedback"
    assert client.get("/api/v1/feedback").json()[0]["message"] == "Canal gate is broken"
    with session_factory() as session:
        assert session.scalar(select(CommunityFeedback)).reporter_id is None


def test_unknown_keyword_returns_help(client):
    reply = send(client, "hello there")
    assert reply["record_type"] is None and "*801#" in reply["reply"]
