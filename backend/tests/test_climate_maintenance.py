"""Coverage-aware climate evidence and explicit outage/repair history."""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.db.models import AssetMaintenance, AssetOutage, Cell, IrrigationClimateLog, IrrigationScheme, PlatformAccount, RainfallReference, SchemeAsset, Sector, UserRole
from app.services.climate import daily_summary
from app.services.maintenance import interval_hours
from app.services.rainfall import aggregate_gauges

START = date(2026, 10, 1)
END = date(2026, 10, 2)


def rain(day=START, mm=0, **changes):
    values = dict(id=1, rainfall_mm=mm, observation_date=day, gauge_code="gauge-A", reporter_id=None,
                  cell_id=1, verification_status="verified", data_source="Manual gauge sheet",
                  created_at=datetime(2026, 10, 5, tzinfo=timezone.utc))
    values.update(changes)
    return SimpleNamespace(**values)


def test_zero_rain_is_a_measurement_and_missing_is_null():
    summary = daily_summary([rain()], START, END)
    assert summary["daily"][0]["mean_mm"] == 0
    assert summary["daily"][1]["mean_mm"] is None
    assert summary["missing_days"] == 1 and summary["coverage_percent"] == 50
    assert summary["verified_complete_total_mm"] is None
    totals, counts = aggregate_gauges([("A", datetime.now(timezone.utc), 0)])
    assert totals == {"A": 0} and counts == {"A": 1}


def test_latest_gauge_day_replaces_duplicate_without_summing():
    result = daily_summary([rain(mm=10), rain(mm=20, id=2), rain(END, 0, id=3)], START, END)
    assert result["partial_total_mm"] == result["verified_complete_total_mm"] == 20
    assert result["complete_verified_gauges"] == 1


def test_incomplete_gauges_do_not_reduce_complete_verified_total():
    result = daily_summary([rain(mm=10), rain(END, 20, id=2), rain(mm=100, gauge_code="B", id=3)], START, END)
    assert result["verified_complete_total_mm"] == 30
    assert result["partial_total_mm"] == 75  # daily mean 55 + next day 20; explicitly partial
    assert result["coverage_percent"] == 75


@pytest.mark.parametrize("changes", [{"verification_status": "unverified"}, {"data_source": None}, {"observation_date": None}, {"verification_status": "rejected"}])
def test_ineligible_or_receipt_date_only_readings_cannot_support_anomaly(changes):
    assert daily_summary([rain(**changes)], START, START)["verified_complete_total_mm"] is None


def test_unknown_gauges_are_not_fabricated_and_outliers_are_not_clamped():
    summary = daily_summary([rain(mm=500), rain(mm=9, gauge_code=None, id=2)], START, START)
    assert summary["partial_total_mm"] == 500
    assert summary["unknown_gauge_reports"] == 1


@pytest.fixture
def climate_world(db, district):
    scheme_id = db.scalar(select(IrrigationScheme.id).where(IrrigationScheme.name == "APEFA Solar"))
    for day, mm in ((START, 10), (END, 20)):
        db.add(IrrigationClimateLog(cell_id=district["cell_id"], scheme_id=scheme_id, rainfall_mm=mm,
            observation_date=day, gauge_code="A", data_source="Gauge sheet", verification_status="verified",
            created_at=datetime(2026, 10, 20, tzinfo=timezone.utc)))
    asset = SchemeAsset(scheme_id=scheme_id, cell_id=district["cell_id"], name_en="Test pump", name_rw="Test pump", asset_type="pump")
    db.add(asset)
    db.commit()
    return {**district, "scheme_id": scheme_id, "asset_id": asset.id}


def reference_payload(world, **changes):
    values = dict(sector_id=world["sector_id"], period_start="2026-10-01", period_end="2026-10-02",
                  reference_start_year=1991, reference_end_year=2020, mean_rainfall_mm=20,
                  source="Synthetic test reference", document_reference="Fixture table 1")
    values.update(changes)
    return values


def test_reference_requires_approval_and_matching_location_period(client, climate_world):
    created = client.post("/api/v1/climate/references", json=reference_payload(climate_world))
    assert created.status_code == 201
    ref_id = created.json()["id"]
    params = dict(start="2026-10-01", end="2026-10-02", sector_id=climate_world["sector_id"], reference_id=ref_id)
    assert client.get("/api/v1/climate/rainfall", params=params).json()["anomaly"]["status"] == "reference_not_approved"
    assert client.post(f"/api/v1/climate/references/{ref_id}/approve", json={"approved_at": "2026-09-01"}).status_code == 200
    result = client.get("/api/v1/climate/rainfall", params=params).json()
    assert result["summary"]["verified_complete_total_mm"] == 30
    assert result["anomaly"]["percent"] == 50 and result["anomaly"]["difference_mm"] == 10
    assert result["by_scheme"][0]["partial_total_mm"] == 30
    # Late receipt (Oct 20) does not relocate Oct 1/2 observations.
    assert result["summary"]["daily"][0]["date"] == "2026-10-01"
    assert client.get("/api/v1/climate/rainfall", params={**params, "end": "2026-10-03"}).json()["anomaly"]["status"] == "reference_location_or_period_mismatch"


def test_demo_and_simulator_rain_do_not_enter_real_totals(client, db, climate_world):
    for origin in ("demo", "simulator"):
        db.add(IrrigationClimateLog(rainfall_mm=99, observation_date=START, gauge_code=origin,
                                   data_origin=origin, cell_id=climate_world["cell_id"]))
    db.commit()
    result = client.get("/api/v1/climate/rainfall", params={"start": str(START), "end": str(END)}).json()
    assert result["summary"]["partial_total_mm"] == 30


def test_zero_reference_has_absolute_anomaly_but_no_percentage(client, climate_world):
    ref = client.post("/api/v1/climate/references", json=reference_payload(climate_world, mean_rainfall_mm=0)).json()
    client.post(f"/api/v1/climate/references/{ref['id']}/approve", json={"approved_at": "2026-09-01"})
    result = client.get("/api/v1/climate/rainfall", params={"start": str(START), "end": str(END), "sector_id": climate_world["sector_id"], "reference_id": ref["id"]}).json()
    assert result["anomaly"]["difference_mm"] == 30 and result["anomaly"]["percent"] is None


@pytest.mark.parametrize("changes", [{"source": " "}, {"reference_end_year": 2026}, {"mean_rainfall_mm": -1}, {"period_end": "2026-09-01"}, {"sector_id": None}])
def test_bad_reference_inputs_are_rejected(client, climate_world, changes):
    assert client.post("/api/v1/climate/references", json=reference_payload(climate_world, **changes)).status_code == 422


def test_demo_reference_cannot_be_approved(client, climate_world):
    ref = client.post("/api/v1/climate/references", json=reference_payload(climate_world, data_origin="demo")).json()
    assert client.post(f"/api/v1/climate/references/{ref['id']}/approve", json={"approved_at": "2026-09-01"}).status_code == 422


def outage_payload(world, **changes):
    return {"asset_id": world["asset_id"], "started_at": "2026-10-01T08:00:00+02:00", "category": "technical",
            "description": "Test motor fault", "source": "Synthetic operator sheet", **changes}


def maintenance_payload(world, **changes):
    return {"asset_id": world["asset_id"], "performed_at": "2026-10-01T14:00:00+02:00", "kind": "repair",
            "action": "Test motor replaced and tested", "source": "Synthetic repair sheet", "restored": True, **changes}


def test_outage_repair_closes_interval_and_keeps_audit_history(client, db, climate_world):
    out = client.post("/api/v1/irrigation/outages", json=outage_payload(climate_world))
    assert out.status_code == 201
    oid = out.json()["id"]
    assert client.post("/api/v1/irrigation/outages", json=outage_payload(climate_world)).status_code == 409
    repaired = client.post("/api/v1/irrigation/maintenance", json=maintenance_payload(climate_world, outage_id=oid))
    assert repaired.status_code == 201
    result = client.get("/api/v1/irrigation/maintenance?start=2026-10-01&end=2026-10-02").json()["assets"][0]
    assert result["recorded_downtime_hours"] == 6
    assert result["open_outages"] == 0 and result["outages"][0]["repair_status"] == "repaired"
    assert len(result["maintenance"]) == 1
    assert client.post("/api/v1/irrigation/maintenance", json=maintenance_payload(climate_world, outage_id=oid)).status_code == 409
    assert db.scalar(select(AssetMaintenance).where(AssetMaintenance.outage_id == oid)) is not None


def test_no_records_means_unknown_and_demo_outages_do_not_count(client, climate_world):
    client.post("/api/v1/irrigation/outages", json=outage_payload(climate_world, data_origin="demo"))
    asset = client.get("/api/v1/irrigation/maintenance?start=2026-10-01&end=2026-10-02").json()["assets"][0]
    assert asset["recorded_downtime_hours"] is None and asset["outage_count"] == 0
    assert client.post("/api/v1/irrigation/outages", json=outage_payload(climate_world)).status_code == 201


def test_interval_union_clips_window_and_never_double_counts():
    dt = lambda hour: datetime(2026, 10, 1, hour, tzinfo=timezone.utc)
    outages = [SimpleNamespace(started_at=dt(1), ended_at=dt(5)), SimpleNamespace(started_at=dt(3), ended_at=dt(8)),
               SimpleNamespace(started_at=dt(9), ended_at=None)]
    assert interval_hours(outages, dt(2), dt(10)) == 7


@pytest.mark.parametrize("changes", [{"performed_at": "2026-10-01T01:00:00Z"}, {"performed_at": "2026-10-01T14:00:00"}, {"kind": "inspection"}, {"data_origin": "demo"}])
def test_invalid_restoration_is_rejected(client, climate_world, changes):
    out = client.post("/api/v1/irrigation/outages", json=outage_payload(climate_world)).json()
    assert client.post("/api/v1/irrigation/maintenance", json=maintenance_payload(climate_world, outage_id=out["id"], **changes)).status_code == 422


def test_monitor_cannot_write_reference_or_outage(auth, client, climate_world):
    headers = auth(role=UserRole.citizen_science_monitor)
    assert client.post("/api/v1/climate/references", headers=headers, json=reference_payload(climate_world)).status_code == 403
    assert client.post("/api/v1/irrigation/outages", headers=headers, json=outage_payload(climate_world)).status_code == 403


def test_sector_scope_hides_other_assets_and_references(auth, client, db, climate_world):
    headers = auth(role=UserRole.district_officer)
    other = Sector(name="Other sector")
    db.add(other)
    db.flush()
    account = db.scalar(select(PlatformAccount))
    account.sectors = [other]
    db.commit()
    assert client.get("/api/v1/irrigation/maintenance", headers=headers).json()["assets"] == []
    assert client.post("/api/v1/irrigation/outages", headers=headers, json=outage_payload(climate_world)).status_code == 404
    assert client.get("/api/v1/climate/rainfall", headers=headers, params={"sector_id": climate_world["sector_id"]}).status_code == 404


def test_asset_with_history_cannot_be_deleted(client, climate_world):
    client.post("/api/v1/irrigation/outages", json=outage_payload(climate_world))
    assert client.delete(f"/api/v1/scheme-assets/{climate_world['asset_id']}").status_code == 409


def test_legacy_receipt_date_uses_kigali_calendar_day():
    row = rain(observation_date=None, created_at=datetime(2026, 10, 1, 23, tzinfo=timezone.utc))
    result = daily_summary([row], END, END)
    assert result["observed_days"] == 1 and result["legacy_date_reports"] == 1
    assert result["verified_complete_total_mm"] is None


@pytest.mark.parametrize("values,expected", [([0] * 7, {1: 0}), ([0, 0, None, 0, 0, 0, 0], {}), ([0] * 6, {})])
def test_missing_forecast_values_do_not_become_zero_rain(monkeypatch, values, expected):
    from app.services import forecast
    from app.core.config import Settings
    monkeypatch.setattr(forecast, "get_settings", lambda: Settings(_env_file=None, weather_forecast_enabled=True))
    monkeypatch.setattr(forecast, "_cache", {})
    monkeypatch.setattr(forecast.httpx, "get", lambda *a, **kw: SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"daily": {"precipitation_sum": values}}))
    assert forecast.rainfall_forecast({1: (-2, 30)}) == expected


def test_advice_uses_observation_date_and_excludes_rejected_readings(client, db, climate_world):
    from app.schemas.reports import today
    from app.services.advisory import rainfall_by_sector
    base = {"cell_id": climate_world["cell_id"], "rainfall_mm": 100}
    client.post("/api/v1/irrigation-reports", json={**base, "observation_date": str(today() - timedelta(days=10))})
    zero = client.post("/api/v1/irrigation-reports", json={**base, "rainfall_mm": 0, "observation_date": str(today())})
    assert zero.status_code == 201
    rejected = client.post("/api/v1/irrigation-reports", json={**base, "observation_date": str(today())}).json()
    client.patch(f"/api/v1/field-reports/infrastructure/{rejected['id']}/verification", json={"status": "rejected", "note": "Gauge malfunction"})
    assert rainfall_by_sector(db)[climate_world["sector_id"]] == (0, 1)


def test_restoration_cannot_precede_an_existing_inspection(client, climate_world):
    out = client.post("/api/v1/irrigation/outages", json=outage_payload(climate_world)).json()
    inspect = maintenance_payload(climate_world, outage_id=out["id"], kind="inspection", restored=False,
                                 performed_at="2026-10-01T15:00:00+02:00")
    assert client.post("/api/v1/irrigation/maintenance", json=inspect).status_code == 201
    assert client.post("/api/v1/irrigation/maintenance", json=maintenance_payload(climate_world, outage_id=out["id"])).status_code == 422
