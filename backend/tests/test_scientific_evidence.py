"""Scientific comparability, source isolation, approval, corrections and scope regressions."""
from datetime import date

import pytest
from sqlalchemy import select

from app.db.models import AuditEvent, CitizenScienceLog, IrrigationScheme, SchemeBaseline, Sector, Cell, UserRole
from app.services.evaluation import evaluate
from app.services.yield_evaluation import evaluate_yield, tonnes


def baseline(db, scheme_id, **changes):
    values = dict(scheme_id=scheme_id, crop_type="Rice", season="A", reference_year=2026,
                  expected_yield=4000, yield_unit="kg/ha", official_source="District study",
                  document_reference="Study p.12", data_origin="import", verification_status="verified",
                  approved_at=date(2026, 1, 1))
    values.update(changes)
    target = SchemeBaseline(**values)
    db.add(target)
    db.flush()
    return target


def observation(db, scheme_id, **changes):
    values = dict(scheme_id=scheme_id, crop_type="rice", season="a", reference_year=2026,
                  reported_harvest_tons=6, cultivated_area_hectares=3, harvested_area_hectares=2,
                  harvest_date=date(2026, 8, 1), observation_type="measured", data_source="Weighed at cooperative",
                  data_origin="field", verification_status="verified")
    values.update(changes)
    report = CitizenScienceLog(**values)
    db.add(report)
    db.flush()
    return report


@pytest.fixture
def scheme(db):
    scheme = IrrigationScheme(name="Scientific pilot", is_active=True)
    db.add(scheme)
    db.flush()
    return scheme


def test_weighted_yield_uses_harvested_area_and_compatible_units(db, scheme):
    baseline(db, scheme.id)
    observation(db, scheme.id)
    observation(db, scheme.id, reported_harvest_tons=2, harvested_area_hectares=0.5)
    result = evaluate_yield(db, scheme.id)
    assert result["value"] == 80  # 8 tonnes / 2.5 harvested ha / 4 t/ha
    assert result["comparisons"][0]["observed_tons_per_hectare"] == 3.2
    assert result["comparisons"][0]["eligible_reports"] == 2


@pytest.mark.parametrize("changes", [
    {"crop_type": "Maize"}, {"season": "B"}, {"reference_year": 2025},
    {"verification_status": "unverified"}, {"verification_status": "rejected"},
    {"data_origin": "demo"}, {"data_origin": "simulator"}, {"superseded_by_id": 123},
    {"harvested_area_hectares": None}, {"harvested_area_hectares": 0},
    {"reported_harvest_tons": None}, {"observation_type": "farmer_estimate"},
    {"observation_type": "historical_reference"}, {"data_source": " "}, {"harvest_date": None},
])
def test_ineligible_observations_never_produce_achievement(db, scheme, changes):
    baseline(db, scheme.id)
    observation(db, scheme.id, **changes)
    assert evaluate_yield(db, scheme.id)["value"] is None


@pytest.mark.parametrize("changes", [
    {"verification_status": "unverified"}, {"data_origin": "demo"},
    {"approved_at": None}, {"official_source": " "}, {"document_reference": " "},
])
def test_unapproved_or_unsourced_targets_are_not_baselines(db, scheme, changes):
    baseline(db, scheme.id, **changes)
    observation(db, scheme.id)
    assert not evaluate_yield(db, scheme.id)["comparisons"]


def test_zero_observed_yield_is_a_valid_zero_percent(db, scheme):
    baseline(db, scheme.id)
    observation(db, scheme.id, reported_harvest_tons=0)
    assert evaluate_yield(db, scheme.id)["value"] == 0


def test_multiple_seasons_are_kept_separate(db, scheme):
    baseline(db, scheme.id)
    baseline(db, scheme.id, season="B")
    observation(db, scheme.id)
    observation(db, scheme.id, season="B")
    result = evaluate_yield(db, scheme.id)
    assert result["value"] is None
    assert [c["value"] for c in result["comparisons"]] == [75, 75]


def test_draft_replacement_does_not_retire_approved_target(db, scheme):
    first = baseline(db, scheme.id)
    replacement = baseline(db, scheme.id, supersedes_id=first.id, expected_yield=3000, verification_status="unverified")
    observation(db, scheme.id)
    assert evaluate_yield(db, scheme.id)["value"] == 75
    replacement.verification_status = "verified"
    db.flush()
    assert evaluate_yield(db, scheme.id)["value"] == 100


@pytest.mark.parametrize("quantity,unit,expected", [(1000, "kg", 1), (1.25, "t", 1.25), (0, "kg", 0)])
def test_unit_conversion(quantity, unit, expected):
    assert tonnes(quantity, unit) == expected


@pytest.mark.parametrize("quantity,unit", [(-1, "t"), (float("inf"), "t"), (float("nan"), "kg"), (1, "bags")])
def test_invalid_units_and_numbers(quantity, unit):
    with pytest.raises(ValueError):
        tonnes(quantity, unit)


def test_api_requires_explicit_approval_and_keeps_versions(client, district, session_factory):
    with session_factory() as db:
        scheme_id = db.scalar(select(IrrigationScheme.id).where(IrrigationScheme.name == "APEFA Solar"))
    payload = dict(scheme_id=scheme_id, crop_type="Rice", season="A", reference_year=2026,
                   expected_yield=4, yield_unit="t/ha", official_source="District study", document_reference="p.12")
    created = client.post("/api/v1/scheme-baselines", json=payload)
    assert created.status_code == 201
    first = created.json()["id"]
    assert created.json()["verification_status"] == "unverified"
    assert client.post(f"/api/v1/scheme-baselines/{first}/approve", json={"approved_at": "2026-01-01"}).status_code == 200
    duplicate = client.post("/api/v1/scheme-baselines", json=payload).json()["id"]
    assert client.post(f"/api/v1/scheme-baselines/{duplicate}/approve", json={"approved_at": "2026-01-01"}).status_code == 409
    next_id = client.post("/api/v1/scheme-baselines", json={**payload, "supersedes_id": first}).json()["id"]
    assert client.post(f"/api/v1/scheme-baselines/{next_id}/approve", json={"approved_at": "2026-01-01"}).status_code == 200
    demo = client.post("/api/v1/scheme-baselines", json={**payload, "data_origin": "demo"}).json()["id"]
    assert client.post(f"/api/v1/scheme-baselines/{demo}/approve", json={"approved_at": "2026-01-01"}).status_code == 422


@pytest.mark.parametrize("changes", [
    {"harvested_area_hectares": 4, "cultivated_area_hectares": 3},
    {"observed_quantity": 10}, {"harvest_unit": "kg"},
    {"observed_quantity": 1000, "harvest_unit": "kg", "reported_harvest_tons": 2},
    {"planting_date": "2026-08-10", "harvest_date": "2026-08-01"},
    {"harvest_date": "2099-01-01"}, {"crop_type": " "},
])
def test_invalid_measurements_are_rejected(client, changes):
    assert client.post("/api/v1/citizen-reports", json={"crop_type": "Rice", **changes}).status_code == 422


def test_legacy_area_is_not_inferred_and_kg_are_normalized(client):
    legacy = client.post("/api/v1/citizen-reports", json={"crop_type": "Rice", "reported_harvest_tons": 4, "cultivated_area_hectares": 2}).json()
    assert legacy["yield_tons_per_hectare"] is None
    measured = client.post("/api/v1/citizen-reports", json={"crop_type": "Rice", "observed_quantity": 1000, "harvest_unit": "kg", "harvested_area_hectares": 0.5}).json()
    assert measured["reported_harvest_tons"] == 1
    assert measured["yield_tons_per_hectare"] == 2


def test_correction_retains_original_and_requires_new_verification(client, district, session_factory):
    created = client.post("/api/v1/citizen-reports", json={"crop_type": "Rice", "reported_harvest_tons": 4, "cell_id": district["cell_id"]}).json()
    original_id = created["id"]
    client.patch(f"/api/v1/field-reports/crop/{original_id}/verification", json={"status": "verified"})
    corrected = client.post(f"/api/v1/field-reports/crop/{original_id}/corrections", json={"reason": "Reweighed harvest", "changes": {"reported_harvest_tons": 3}})
    assert corrected.status_code == 201
    replacement_id = corrected.json()["id"]
    assert client.get(f"/api/v1/field-reports/crop/{original_id}").status_code == 200
    assert client.patch(f"/api/v1/field-reports/crop/{original_id}/verification", json={"status": "verified"}).status_code == 409
    assert client.post(f"/api/v1/field-reports/crop/{original_id}/corrections", json={"reason": "Again", "changes": {"reported_harvest_tons": 2}}).status_code == 409
    with session_factory() as db:
        original = db.get(CitizenScienceLog, original_id)
        replacement = db.get(CitizenScienceLog, replacement_id)
        assert original.reported_harvest_tons == 4 and original.verification_status == "verified"
        assert original.superseded_by_id == replacement_id
        assert replacement.reported_harvest_tons == 3 and replacement.verification_status == "unverified"
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == "report.corrected")) is not None
    metrics = client.get("/api/v1/analytics/executive-overview").json()["metrics"]
    assert next(m for m in metrics if m["key"] == "citizen_reports")["value"] == 1


def test_real_evaluation_and_legacy_analytics_share_results_and_exclude_demo(db, scheme):
    baseline(db, scheme.id)
    observation(db, scheme.id)
    observation(db, scheme.id, data_origin="demo", reported_harvest_tons=999)
    observation(db, scheme.id, data_origin="simulator", reported_harvest_tons=888)
    db.commit()
    from app.services.analytics import scheme_performance
    modern = evaluate(db)["schemes"][0]
    classic = scheme_performance(db)[0]
    assert modern["outcomes"]["yield_achievement"]["value"] == classic["achievement_percent"] == 75
    assert modern["outcomes"]["reported_tons"] == classic["reported_tons"] == 6
    assert modern["evidence"]["reports"] == 1


def test_monitor_cannot_approve_or_correct(auth, client, district):
    headers = auth(role=UserRole.citizen_science_monitor)
    assert client.post("/api/v1/scheme-baselines/1/approve", headers=headers, json={"approved_at": "2026-01-01"}).status_code == 403
    assert client.post("/api/v1/field-reports/crop/1/corrections", headers=headers, json={"reason": "Check", "changes": {"reported_harvest_tons": 2}}).status_code == 403


def test_sector_scope_protects_correction_and_report_creation(auth, client, district, session_factory):
    from app.db.models import PlatformAccount
    with session_factory() as db:
        other_sector = Sector(name="Other sector")
        db.add(other_sector)
        db.flush()
        cell = Cell(name="Other cell", sector_id=other_sector.id)
        db.add(cell)
        db.flush()
        outside = CitizenScienceLog(crop_type="Rice", cell_id=cell.id)
        db.add(outside)
        db.commit()
        outside_id, cell_id = outside.id, cell.id
    headers = auth(role=UserRole.citizen_science_monitor)
    with session_factory() as db:
        person = db.scalar(select(PlatformAccount))
        person.sectors = [db.get(Sector, district["sector_id"])]
        db.commit()
    assert client.post("/api/v1/citizen-reports", headers=headers, json={"crop_type": "Rice", "cell_id": cell_id}).status_code == 404
    with session_factory() as db:
        db.scalar(select(PlatformAccount)).role = UserRole.district_officer
        db.commit()
    assert client.post(f"/api/v1/field-reports/crop/{outside_id}/corrections", headers=headers,
                       json={"reason": "Move record", "changes": {"reported_harvest_tons": 1}}).status_code == 404


def test_filtering_verification_does_not_hide_duplicate_candidates(client, district):
    first = client.post("/api/v1/citizen-reports", json={"crop_type": "Rice", "reporter_id": 1, "cell_id": district["cell_id"]}).json()["id"]
    client.patch(f"/api/v1/field-reports/crop/{first}/verification", json={"status": "verified"})
    client.post("/api/v1/citizen-reports", json={"crop_type": "Rice", "reporter_id": 1, "cell_id": district["cell_id"]})
    listed = client.get("/api/v1/field-reports?verification=unverified").json()["reports"]
    assert len(listed) == 1 and "possible_duplicate" in listed[0]["flags"]


def test_correction_keeps_case_history_without_new_notifications(client, session_factory):
    from app.db.models import IncidentCase, IncidentEvent, AdvisoryMessage
    original = client.post("/api/v1/irrigation-reports", json={"infrastructure_name": "Pump", "operational_status": "offline"}).json()["id"]
    with session_factory() as db:
        case_id = db.scalar(select(IncidentCase.id))
        events = len(list(db.scalars(select(IncidentEvent))))
        messages = len(list(db.scalars(select(AdvisoryMessage))))
    result = client.post(f"/api/v1/field-reports/infrastructure/{original}/corrections",
                         json={"reason": "Checked pump", "changes": {"operational_status": "faulty"}})
    assert result.status_code == 201
    with session_factory() as db:
        assert db.get(IncidentCase, case_id).source_id == result.json()["id"]
        assert len(list(db.scalars(select(IncidentCase)))) == 1
        assert len(list(db.scalars(select(IncidentEvent)))) == events
        assert len(list(db.scalars(select(AdvisoryMessage)))) == messages


def test_csv_keeps_comparable_groups_and_official_sources_separate(client, db, scheme):
    import csv
    import io
    baseline(db, scheme.id)
    baseline(db, scheme.id, season="B", expected_yield=2000)
    observation(db, scheme.id)
    observation(db, scheme.id, season="B", reported_harvest_tons=2)
    db.commit()
    response = client.get("/api/v1/evaluation/export.csv")
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert len(rows) == 2
    assert {row["season"]: row["yield_achievement"] for row in rows} == {"A": "75.0", "B": "50.0"}
    assert all(row["official_source"] == "District study" and row["source_document"] == "Study p.12" for row in rows)
    assert all(row["eligible_reports"] == "1" for row in rows)
