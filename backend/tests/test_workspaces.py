"""Workspace APIs: field reports and verification, irrigation assets, evaluation, assignees,
the audit log, and nutrition small-group suppression."""
from sqlalchemy import select

from app.db.models import AuditEvent, CitizenScienceLog, IrrigationScheme, NutritionSurvey, UserRole


def scheme_id(session_factory, name="PADAB"):
    with session_factory() as session:
        return session.scalar(select(IrrigationScheme.id).where(IrrigationScheme.name == name))


def sms(client, text, phone="+250788000001"):
    return client.post("/api/v1/sms/inbound", data={"from": phone, "to": "8448", "text": text}).json()


# --- Field reports ------------------------------------------------------------------

def test_field_reports_carry_quality_flags(client, district):
    sms(client, "NZANA 5")
    sms(client, "NZANA 5")  # the same phone, the same pest, minutes later
    sms(client, "IMVURA 400")  # implausible rain
    client.post("/api/v1/citizen-reports", json={"crop_type": "Beans"})  # no location, no measure
    reports = client.get("/api/v1/field-reports").json()["reports"]
    pests = [r for r in reports if r["kind"] == "pest"]
    assert sum("possible_duplicate" in r["flags"] for r in pests) == 1
    assert "unusual_value" in next(r for r in reports if r["kind"] == "rain")["flags"]
    beans = next(r for r in reports if r["crop"] == "Beans")
    assert {"no_location", "missing_measure"} <= set(beans["flags"])
    assert next(r for r in reports if r["kind"] == "rain")["sector"] == "Ngeruka"


def test_field_reports_filter_by_kind_and_leave_out_simulator_tests(client, district):
    sms(client, "IMVURA 12")
    client.post("/api/v1/simulator/sms", json={"from": "+250788000001", "text": "IMVURA 30"})
    sms(client, "NZANA 3")
    rain = client.get("/api/v1/field-reports", params={"kind": "rain"}).json()["reports"]
    assert [r["rainfall_mm"] for r in rain] == [12]


def test_monitors_see_masked_reporters(auth, client, district):
    sms(client, "IMVURA 12")
    monitor = client.get("/api/v1/field-reports", headers=auth("m@example.org", role=UserRole.citizen_science_monitor)).json()
    assert monitor["personal_data"] is False and "•" in monitor["reports"][0]["reporter"]
    officer = client.get("/api/v1/field-reports", headers=auth("o@example.org", role=UserRole.district_officer)).json()
    assert officer["reports"][0]["reporter"] == "+250788000001"


def test_verification_needs_staff_a_reason_to_reject_and_is_audited(auth, client, district, session_factory):
    admin = auth("a@example.org", role=UserRole.administrator)
    report_id = client.post("/api/v1/citizen-reports", headers=admin, json={"cell_id": district["cell_id"], "crop_type": "Maize",
                                                                              "pest_or_disease": "Aphids", "severity": 2}).json()["id"]
    url = f"/api/v1/field-reports/crop/{report_id}/verification"
    monitor = auth("m@example.org", role=UserRole.citizen_science_monitor)
    assert client.patch(url, headers=monitor, json={"status": "verified"}).status_code == 403
    officer = auth("o@example.org", role=UserRole.district_officer)
    assert client.patch(url, headers=officer, json={"status": "rejected"}).status_code == 422
    assert client.patch(url, headers=officer, json={"status": "verified", "note": "Seen on the farm"}).json()["verification_status"] == "verified"
    detail = client.get(f"/api/v1/field-reports/crop/{report_id}", headers=officer).json()
    assert detail["verification_status"] == "verified" and detail["verification_history"][0]["action"] == "report.verified"
    with session_factory() as session:
        assert session.get(CitizenScienceLog, report_id).verified_by_account_id is not None


def test_export_is_for_staff_and_has_no_phone_numbers(auth, client, district):
    sms(client, "IMVURA 12")
    assert client.get("/api/v1/field-reports/export.csv", headers=auth("m@example.org", role=UserRole.citizen_science_monitor)).status_code == 403
    response = client.get("/api/v1/field-reports/export.csv", headers=auth("o@example.org", role=UserRole.district_officer))
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/csv")
    assert "+250788" not in response.text and "Rain gauge: 12 mm" in response.text


# --- Irrigation assets --------------------------------------------------------------

def test_assets_show_the_latest_condition_and_history(client, district, session_factory):
    padab = scheme_id(session_factory)
    for status in ("offline", "operational"):
        client.post("/api/v1/irrigation-reports", json={"cell_id": district["cell_id"], "scheme_id": padab,
                                                        "infrastructure_name": "Pumping Station 1", "operational_status": status})
    body = client.get("/api/v1/irrigation/assets").json()
    asset = body["assets"][0]
    assert asset["status"] == "operational" and asset["down"] is False and asset["fault_reports"] == 1
    assert body["counts"]["down"] == 0
    history = client.get("/api/v1/irrigation/assets/history", params={"asset": "Pumping Station 1", "scheme_id": padab}).json()
    assert [item["condition"] for item in history["history"]] == ["operational", "offline"]
    assert history["history"][1]["case"]["priority"] == "critical"  # the offline report opened a case
    assert client.get("/api/v1/irrigation/assets/history", params={"asset": "Nothing", "scheme_id": padab}).status_code == 404


# --- Evaluation ---------------------------------------------------------------------

def test_evaluation_lists_evidence_and_never_computes_incomparable_yields(client, district, session_factory):
    apefa = scheme_id(session_factory, "APEFA Solar")
    client.post("/api/v1/citizen-reports", json={"cell_id": district["cell_id"], "scheme_id": apefa, "crop_type": "Maize", "reported_harvest_tons": 3})
    body = client.get("/api/v1/evaluation").json()
    assert [q["id"] for q in body["questions"]] == [1, 2, 3, 4, 5]
    row = next(s for s in body["schemes"] if s["name"] == "APEFA Solar")
    assert row["documentation"]["state"] == "documented"
    assert row["outcomes"]["crops"][0] == {"crop": "Maize", "reports": 1, "with_reported_tons": 1, "reported_tons": 3.0, "expected_tons": 0.0}
    achievement = row["outcomes"]["yield_achievement"]
    assert achievement["value"] is None and achievement["computable"] is False
    assert any(not item["met"] for item in achievement["requirements"])
    assert row["evidence"]["located_percent"] == 100.0
    assert next(s for s in body["schemes"] if s["name"] == "PADAB")["documentation"]["state"] == "missing"


def test_evaluation_export_is_for_staff(auth, client, district):
    assert client.get("/api/v1/evaluation/export.csv", headers=auth("m@example.org", role=UserRole.citizen_science_monitor)).status_code == 403
    response = client.get("/api/v1/evaluation/export.csv", headers=auth("p@example.org", role=UserRole.district_planner))
    assert response.status_code == 200 and "not computable" in response.text


# --- Assignees and the audit log ----------------------------------------------------

def test_assignees_and_audit_log(auth, client, district):
    planner = auth("p@example.org", role=UserRole.district_planner)
    admin = auth("a@example.org", role=UserRole.administrator)
    names = [person["full_name"] for person in client.get("/api/v1/admin/assignees", headers=planner).json()]
    assert len(names) == 2  # the planner and the administrator; monitors are not assignable
    client.post("/api/v1/citizen-reports", headers=admin, json={"cell_id": district["cell_id"], "crop_type": "Maize", "pest_or_disease": "Armyworm", "severity": 5})
    case_id = client.get("/api/v1/cases", headers=planner).json()[0]["id"]
    officer_id = client.get("/api/v1/admin/assignees", headers=planner).json()[0]["id"]
    assert client.patch(f"/api/v1/cases/{case_id}", headers=planner, json={"status": "assigned", "assigned_to_account_id": officer_id}).status_code == 200
    assert client.get("/api/v1/admin/audit", headers=planner).status_code == 403
    log = client.get("/api/v1/admin/audit", headers=admin).json()
    assert log[0]["action"] == "case.update" and log[0]["detail"]["assigned_to_account_id"] == officer_id


# --- Nutrition privacy --------------------------------------------------------------

def test_small_nutrition_groups_are_suppressed(client, district, session_factory):
    with session_factory() as session:
        for _ in range(2):
            session.add(NutritionSurvey(cell_id=district["cell_id"], meals_per_day=1, ate_protein_or_vegetables=False, food_sufficient=False, stunting_risk_score=5))
        session.commit()
    body = client.get("/api/v1/analytics/nutrition-summary").json()
    cell = body["by_cell"][0]
    assert cell["households"] == 2 and cell["suppressed"] is True
    assert cell["average_risk"] is None and cell["high_risk"] is None
    assert body["households"] == 2  # district totals still count them
    with session_factory() as session:
        assert session.scalar(select(AuditEvent)) is None  # reading figures is not audited
