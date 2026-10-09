"""Executive overview: metric envelopes, latest asset status, filters, data origin and roles."""
from sqlalchemy import select

from app.db.models import CitizenScienceLog, IrrigationScheme, Sector, UserRole

OVERVIEW = "/api/v1/analytics/executive-overview"


def metrics(body) -> dict:
    return {item["key"]: item for item in body["metrics"]}


def scheme_ids(session_factory) -> dict:
    with session_factory() as session:
        return {scheme.name: scheme.id for scheme in session.scalars(select(IrrigationScheme))}


def asset_report(client, district, scheme_id, name, status, category=None):
    response = client.post("/api/v1/irrigation-reports", json={"cell_id": district["cell_id"], "scheme_id": scheme_id,
                                                                "infrastructure_name": name, "operational_status": status,
                                                                "bottleneck_category": category})
    assert response.status_code == 201


def test_every_metric_carries_its_meaning(client, district):
    body = client.get(OVERVIEW).json()
    assert body["period"]["days"] == 30 and body["demo_mode"] is False
    for item in body["metrics"]:
        assert item["label"] and item["unit"] and item["period"] and item["definition"]
        assert item["source"] in {"live_unverified", "platform", "documented", "demo", "missing"}
    values = metrics(body)
    assert values["citizen_reports"]["value"] == 0
    assert values["rainfall_7d"]["value"] is None and values["rainfall_7d"]["source"] == "missing"
    assert values["assets_down"]["source"] == "missing"
    assert not any("growth" in key or "trend" in key for key in values)


def test_assets_down_uses_the_latest_report_per_asset(client, district, session_factory):
    ids = scheme_ids(session_factory)
    asset_report(client, district, ids["PADAB"], "Pumping Station 1", "offline", "technical")
    asset_report(client, district, ids["PADAB"], "Pumping Station 1", "operational")
    asset_report(client, district, ids["PADAB"], "Canal C4", "faulty", "environmental")
    body = client.get(OVERVIEW).json()
    down = metrics(body)["assets_down"]
    assert down["value"] == 1 and down["note"] == "of 2 assets with a condition report"
    assert [asset["asset"] for asset in body["assets"] if asset["down"]] == ["Canal C4"]
    padab = next(row for row in body["schemes"] if row["name"] == "PADAB")
    assert padab["assets_down"] == 1 and padab["fault_reports"] == 2


def test_yield_achievement_is_never_computed_from_non_comparable_figures(client, district, session_factory):
    ids = scheme_ids(session_factory)
    client.post("/api/v1/citizen-reports", json={"cell_id": district["cell_id"], "scheme_id": ids["APEFA Solar"], "crop_type": "Maize",
                                                 "reported_harvest_tons": 4})
    rows = {row["name"]: row for row in client.get(OVERVIEW).json()["schemes"]}
    apefa = rows["APEFA Solar"]
    assert apefa["reported_harvest"]["value"] == 4
    assert apefa["yield_target"]["value"] == 10 and apefa["yield_target"]["source"] == "documented"
    assert apefa["yield_achievement"]["value"] is None and apefa["yield_achievement"]["source"] == "missing"
    assert "sample" in apefa["yield_achievement"]["note"]
    assert rows["PADAB"]["yield_target"]["source"] == "missing"  # no documented target


def test_simulator_tests_are_left_out_and_demo_rows_are_labelled(client, district, session_factory):
    client.post("/api/v1/simulator/sms", json={"from": "+250788000001", "text": "IMVURA 12"})
    assert metrics(client.get(OVERVIEW).json())["citizen_reports"]["value"] == 0
    with session_factory() as session:
        session.add(CitizenScienceLog(cell_id=district["cell_id"], crop_type="Beans", data_origin="demo"))
        session.commit()
    body = client.get(OVERVIEW).json()
    assert body["demo_mode"] is True
    assert metrics(body)["citizen_reports"] == {**metrics(body)["citizen_reports"], "value": 1, "source": "demo"}


def test_sector_filter_and_coverage(client, district, session_factory):
    with session_factory() as session:
        other = Sector(name="Nyamata")
        session.add(other)
        session.commit()
        other_id = other.id
    client.post("/api/v1/citizen-reports", json={"cell_id": district["cell_id"], "crop_type": "Maize", "pest_or_disease": "Aphids", "severity": 2})
    district_wide = metrics(client.get(OVERVIEW).json())
    assert district_wide["reporting_coverage"]["value"] == 50 and district_wide["reporting_coverage"]["note"] == "1 of 2 sectors"
    elsewhere = metrics(client.get(OVERVIEW, params={"sector_id": other_id}).json())
    assert elsewhere["citizen_reports"]["value"] == 0 and elsewhere["reporting_coverage"]["value"] == 0


def test_filters_are_validated(client, district):
    assert client.get(OVERVIEW, params={"scheme_id": 999}).status_code == 422
    assert client.get(OVERVIEW, params={"sector_id": 999}).status_code == 422
    assert client.get(OVERVIEW, params={"days": 3}).status_code == 422


def test_priority_actions_are_for_district_staff(auth, client, district):
    admin = auth("a@example.org", role=UserRole.administrator)  # the auth fixture already requires sign-in
    created = client.post("/api/v1/citizen-reports", headers=admin,
                          json={"cell_id": district["cell_id"], "crop_type": "Maize", "pest_or_disease": "Fall armyworm", "severity": 5})
    assert created.status_code == 201
    planner = client.get(OVERVIEW, headers=auth("p@example.org", role=UserRole.district_planner)).json()
    assert planner["priority_actions"][0]["priority"] == "critical"
    assert metrics(planner)["critical_incidents"]["value"] == 1
    monitor = client.get(OVERVIEW, headers=auth("m@example.org", role=UserRole.citizen_science_monitor)).json()
    assert monitor["priority_actions"] is None
    assert metrics(monitor)["critical_incidents"]["value"] == 1  # the count is not personal data


def test_invented_demo_targets_are_never_called_documented(client, district, session_factory):
    with session_factory() as session:
        scheme = session.scalar(select(IrrigationScheme).where(IrrigationScheme.name == "PADAB"))
        scheme.baseline_yield_target_tons, scheme.baseline_source = 140, "DEMONSTRATION VALUE - replace with the feasibility-study figure"
        session.commit()
    padab = next(row for row in client.get(OVERVIEW).json()["schemes"] if row["name"] == "PADAB")
    assert padab["yield_target"]["source"] == "demo"
