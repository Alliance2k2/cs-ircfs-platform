"""WP5: cooperatives, the Inteko z'Abaturage participation ranking, Data Champions
and training progress against the 200-monitor target."""
from datetime import date, datetime, timedelta, timezone

from app.core.config import Settings
from app.db.models import (
    CitizenScienceLog,
    Cooperative,
    FieldUser,
    IrrigationClimateLog,
    NutritionSurvey,
    Sector,
    UserRole,
)
from app.services import cooperatives as coop_service
from app.services.reporting import build_monthly_report, month_window

NOW = datetime.now(timezone.utc)


def seed(db):
    """Two cooperatives: A has an active reporter (crop + rain + nutrition today,
    one report 60 days old), B has members but only an old report."""
    sector = Sector(name="Ngeruka", latitude=-2.35, longitude=30.15)
    db.add(sector)
    db.flush()
    coop_a = Cooperative(name="Tiharanige", sector_id=sector.id, is_pilot=True)
    coop_b = Cooperative(name="Kwishima", sector_id=sector.id)
    db.add_all([coop_a, coop_b])
    db.flush()
    reporter = FieldUser(
        phone_number="+250788000011",
        full_name="Active reporter",
        role=UserRole.citizen_science_monitor,
        cooperative_id=coop_a.id,
        is_data_champion=True,
        trained_at=date(2026, 9, 1),
    )
    quiet = FieldUser(phone_number="+250788000012", full_name="Quiet member", cooperative_id=coop_a.id)
    other = FieldUser(phone_number="+250788000013", full_name="Other member", cooperative_id=coop_b.id)
    db.add_all([reporter, quiet, other])
    db.flush()
    recent = NOW - timedelta(hours=1)
    db.add(CitizenScienceLog(reporter_id=reporter.id, crop_type="Maize", created_at=recent))
    db.add(IrrigationClimateLog(reporter_id=reporter.id, rainfall_mm=12.5, created_at=recent - timedelta(minutes=10)))
    db.add(NutritionSurvey(reporter_id=reporter.id, meals_per_day=2, ate_protein_or_vegetables=True,
                           food_sufficient=True, stunting_risk_score=2, created_at=recent - timedelta(minutes=20)))
    db.add(CitizenScienceLog(reporter_id=other.id, crop_type="Rice", created_at=NOW - timedelta(days=60)))
    db.commit()
    return {"cooperative_a": coop_a.id, "cooperative_b": coop_b.id, "reporter": reporter.id}


def test_ranking_counts_reports_and_orders_by_them(db):
    seed(db)
    rows = coop_service.ranking(db)
    assert [row["name"] for row in rows] == ["Tiharanige", "Kwishima"]
    top, bottom = rows
    assert top["reports_30d"] == 3
    assert top["crop_reports_30d"] == 1
    assert top["irrigation_reports_30d"] == 1
    assert top["nutrition_surveys_30d"] == 1
    assert top["active_reporters_30d"] == 1
    assert top["members"] == 2 and top["data_champions"] == 1 and top["is_pilot"] is True
    # The 60-day-old report is outside every current window but sets last_report_at.
    assert bottom["reports_30d"] == 0 and bottom["reports_mtd"] == 0
    assert bottom["members"] == 1 and bottom["data_champions"] == 0
    assert bottom["last_report_at"] is not None
    assert top["last_report_at"] >= bottom["last_report_at"]


def test_ranking_month_to_date_uses_kigali_month(db):
    seed(db)
    rows = coop_service.ranking(db)
    start, end, _ = month_window(None)  # same window the monthly report uses
    stamps = [NOW - timedelta(hours=1), NOW - timedelta(hours=1, minutes=10), NOW - timedelta(hours=1, minutes=20)]
    expected_mtd = sum(1 for stamp in stamps if start <= stamp < end)
    assert rows[0]["reports_mtd"] == expected_mtd


def test_training_progress_against_target(db, monkeypatch):
    seed(db)
    second_monitor = FieldUser(phone_number="+250788000014", role=UserRole.citizen_science_monitor, trained_at=date(2026, 9, 10))
    untrained = FieldUser(phone_number="+250788000015", role=UserRole.citizen_science_monitor)
    db.add_all([second_monitor, untrained])
    db.commit()
    monkeypatch.setattr(
        coop_service,
        "get_settings",
        lambda: Settings(_env_file=None, monitor_training_target=4, pilot_cooperative_target=1),
    )
    progress = coop_service.training_progress(db)
    assert progress["trained_monitors"] == 2
    assert progress["monitors_total"] == 3
    assert progress["target"] == 4 and progress["percent"] == 50.0
    assert progress["data_champions"] == 1
    assert progress["pilot_cooperatives"] == 1 and progress["pilot_target"] == 1
    assert progress["trained_on"] == date(2026, 9, 10)


def test_monthly_report_includes_cooperative_participation(db):
    seed(db)
    report = build_monthly_report(db)
    rows = report["cooperatives"]
    assert [row["name"] for row in rows] == ["Tiharanige", "Kwishima"]
    start, end, _ = month_window(None)
    stamps = [NOW - timedelta(hours=1), NOW - timedelta(hours=1, minutes=10), NOW - timedelta(hours=1, minutes=20)]
    expected = sum(1 for stamp in stamps if start <= stamp < end)
    assert rows[0]["reports_total"] == expected
    assert rows[0]["members"] == 2 and rows[0]["data_champions"] == 1


def test_cooperative_crud_and_member_guard(client):
    created = client.post("/api/v1/cooperatives", json={"name": "Test Coop", "is_pilot": True})
    assert created.status_code == 201 and created.json()["is_pilot"] is True
    cooperative_id = created.json()["id"]
    assert client.post("/api/v1/cooperatives", json={"name": "test coop"}).status_code == 409
    farmer = client.post("/api/v1/field-users", json={"phone_number": "+250788111333", "cooperative_id": cooperative_id})
    assert farmer.status_code == 201 and farmer.json()["cooperative_id"] == cooperative_id
    # Members block deletion until they are moved out.
    assert client.delete(f"/api/v1/cooperatives/{cooperative_id}").status_code == 409
    moved = client.patch(f"/api/v1/field-users/{farmer.json()['id']}", json={"cooperative_id": None})
    assert moved.status_code == 200
    renamed = client.patch(f"/api/v1/cooperatives/{cooperative_id}", json={"name": "Renamed Coop", "is_pilot": False})
    assert renamed.status_code == 200 and renamed.json()["name"] == "Renamed Coop"
    assert client.delete(f"/api/v1/cooperatives/{cooperative_id}").status_code == 204


def test_cooperative_references_are_validated(client):
    assert client.post("/api/v1/cooperatives", json={"name": "Bad Refs", "sector_id": 999}).status_code == 422
    assert client.post("/api/v1/field-users", json={"phone_number": "+250788111444", "cooperative_id": 999}).status_code == 422


def test_field_user_training_fields_round_trip(client):
    coop = client.post("/api/v1/cooperatives", json={"name": "Champions Coop"}).json()
    created = client.post("/api/v1/field-users", json={"phone_number": "+250788111555"}).json()
    updated = client.patch(
        f"/api/v1/field-users/{created['id']}",
        json={
            "cooperative_id": coop["id"],
            "is_data_champion": True,
            "trained_at": "2026-09-15",
            "training_notes": "Rain gauge training in Nyamata",
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["cooperative_id"] == coop["id"]
    assert body["is_data_champion"] is True
    assert body["trained_at"] == "2026-09-15"
    assert body["training_notes"] == "Rain gauge training in Nyamata"


def test_monitor_cannot_read_or_write_cooperatives(client, auth):
    headers = auth(role=UserRole.citizen_science_monitor)
    assert client.get("/api/v1/cooperatives", headers=headers).status_code == 403
    assert client.get("/api/v1/cooperatives/participation", headers=headers).status_code == 403
    assert client.get("/api/v1/cooperatives/training-progress", headers=headers).status_code == 403
    assert client.post("/api/v1/cooperatives", json={"name": "Nope"}, headers=headers).status_code == 403


def test_officer_reads_but_cannot_write_cooperatives(client, auth):
    headers = auth(role=UserRole.district_officer)
    assert client.get("/api/v1/cooperatives", headers=headers).status_code == 200
    assert client.get("/api/v1/cooperatives/participation", headers=headers).status_code == 200
    assert client.post("/api/v1/cooperatives", json={"name": "Nope"}, headers=headers).status_code == 403


def test_planner_and_administrator_manage_cooperatives(client, auth):
    headers = auth(role=UserRole.district_planner)
    created = client.post("/api/v1/cooperatives", json={"name": "Planner Coop"}, headers=headers)
    assert created.status_code == 201
    assert client.get("/api/v1/cooperatives/training-progress", headers=headers).status_code == 200


def test_participation_endpoint_returns_ranking(client):
    client.post("/api/v1/cooperatives", json={"name": "Solo Coop"})
    rows = client.get("/api/v1/cooperatives/participation").json()
    assert [row["name"] for row in rows] == ["Solo Coop"]
    assert rows[0]["reports_30d"] == 0 and rows[0]["reports_mtd"] == 0
    assert rows[0]["members"] == 0 and rows[0]["last_report_at"] is None
