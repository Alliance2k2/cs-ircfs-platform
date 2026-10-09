"""Report creation: automatic cases, USSD idempotency, and nutrition scoring."""
from sqlalchemy import select

from app.db.models import IncidentCase


def cases(session_factory):
    with session_factory() as session:
        return list(session.scalars(select(IncidentCase)))


def test_severe_pest_creates_case(client, session_factory):
    client.post("/api/v1/citizen-reports", json={"crop_type": "Maize", "pest_or_disease": "Fall armyworm", "severity": 5})
    found = cases(session_factory)
    assert len(found) == 1 and found[0].priority == "critical" and found[0].source_type == "crop"


def test_mild_pest_creates_no_case(client, session_factory):
    client.post("/api/v1/citizen-reports", json={"crop_type": "Maize", "pest_or_disease": "Aphids", "severity": 3})
    assert cases(session_factory) == []


def test_offline_infrastructure_creates_critical_case(client, session_factory):
    client.post("/api/v1/irrigation-reports", json={"infrastructure_name": "Pump A", "operational_status": "offline"})
    found = cases(session_factory)
    assert len(found) == 1 and found[0].priority == "critical" and found[0].source_type == "infrastructure"


def test_operational_infrastructure_creates_no_case(client, session_factory):
    client.post("/api/v1/irrigation-reports", json={"infrastructure_name": "Pump A", "operational_status": "operational"})
    assert cases(session_factory) == []


def test_duplicate_ussd_session_is_idempotent(client):
    # Harvest now asks crop, variety, planting month, weeks to harvest, then tons.
    payload = {"sessionId": "dup-session", "phoneNumber": "+250788000001", "text": "1*2*1*1*8*8"}
    first = client.post("/api/v1/ussd?explain=true", json=payload).json()
    retry = client.post("/api/v1/ussd?explain=true", json=payload).json()
    assert retry["reply_status"] == "duplicate"
    assert retry["record_id"] == first["record_id"]
    assert len(client.get("/api/v1/citizen-reports").json()) == 1


def test_trends_count_planting_updates_per_month(client, session_factory):
    """WP1: crop reports that carry a planting date show up as planting updates."""
    from datetime import date

    client.post("/api/v1/citizen-reports", json={"crop_type": "Maize", "planting_date": date.today().isoformat(), "expected_harvest_tons": 2})
    client.post("/api/v1/citizen-reports", json={"crop_type": "Rice", "expected_harvest_tons": 3})
    from app.services.reporting import build_trends

    with session_factory() as session:
        months = build_trends(session)["months"]
    assert months[-1]["plantings"] == 1
    assert months[-1]["expected_tons"] == 5


def test_nutrition_survey_computes_risk_score(client):
    response = client.post(
        "/api/v1/nutrition-surveys",
        json={"meals_per_day": 1, "ate_protein_or_vegetables": False, "food_sufficient": False},
    )
    assert response.status_code == 201
    assert response.json()["stunting_risk_score"] == 5
