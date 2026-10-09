"""WP7: calibration tooling — per-sector rainfall thresholds, the configurable
recurring-bottleneck rule with its AfDB baseline, the two USSD menus moved into
tables, and the import scripts (all values come from documents, never invented)."""
import importlib.util
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.core.config import Settings
from app.db.models import (
    AdvisoryThreshold,
    BottleneckBaseline,
    Cell,
    CommunityFeedback,
    GrievanceCategory,
    IrrigationClimateLog,
    IrrigationScheme,
    SchemeAsset,
    Sector,
    FieldUser,
    UserRole,
)
from app.services import advisory, analytics, ussd

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_sector(db, name="Ngeruka"):
    sector = Sector(name=name, latitude=-2.35, longitude=30.15)
    db.add(sector)
    db.flush()
    return sector


def seed_report_world(db):
    """A sector, a cell with a registered caller, and one irrigation scheme."""
    sector = seed_sector(db)
    cell = Cell(name="Gihembe", sector_id=sector.id, latitude=-2.34, longitude=30.16)
    db.add(cell)
    db.flush()
    scheme = IrrigationScheme(name="PADAB Test", sector_id=sector.id)
    db.add(scheme)
    db.flush()
    user = FieldUser(phone_number="+250788000001", role=UserRole.citizen_science_monitor, cell_id=cell.id)
    db.add(user)
    db.commit()
    return sector, cell, scheme, user


# ---------- Per-sector rainfall thresholds ----------


def test_calibrated_thresholds_override_env_defaults(db, monkeypatch):
    monkeypatch.setattr(advisory, "get_settings", lambda: Settings(_env_file=None, dry_spell_threshold_mm=10, wet_spell_threshold_mm=40))
    sector = seed_sector(db)
    other = seed_sector(db, "Mareba")
    db.add(AdvisoryThreshold(sector_id=sector.id, dry_mm=5.0, wet_mm=25.0, source="neruka_2019_2024.csv", valid_from=date(2026, 1, 1)))
    db.commit()
    # 7 mm is below the .env default dry threshold (10) but above the calibrated one.
    assert advisory.advice_for_rainfall(7, 1).level == "irrigate_more"
    assert advisory.advice_for_rainfall(7, 1, advisory.threshold_map(db).get(sector.id)).level == "normal"
    assert advisory.advice_for_rainfall(30, 1, advisory.threshold_map(db).get(sector.id)).level == "irrigate_less"
    # The schedule reports which thresholds applied, and where they came from.
    rows = {row["sector_id"]: row for row in advisory.sector_schedule(db)}
    assert (rows[sector.id]["threshold_dry_mm"], rows[sector.id]["threshold_wet_mm"]) == (5.0, 25.0)
    assert rows[sector.id]["threshold_source"] == "neruka_2019_2024.csv"
    # A sector without a calibrated row keeps the environment defaults and shows no source.
    assert (rows[other.id]["threshold_dry_mm"], rows[other.id]["threshold_wet_mm"]) == (10.0, 40.0)
    assert rows[other.id]["threshold_source"] is None


def test_local_tip_uses_sector_thresholds(db, monkeypatch):
    monkeypatch.setattr(advisory, "get_settings", lambda: Settings(_env_file=None, dry_spell_threshold_mm=10, wet_spell_threshold_mm=40))
    sector, cell, _, user = seed_report_world(db)
    # One 7 mm reading: below the .env dry threshold (10) but above the calibrated one (0).
    db.add(IrrigationClimateLog(cell_id=cell.id, rainfall_mm=7.0, reporter_id=None))
    db.add(AdvisoryThreshold(sector_id=sector.id, dry_mm=0.0, wet_mm=1000.0, source="calibrated.csv"))
    db.commit()
    tip = advisory.local_tip(db, user)
    assert "Ongera kuhira ho 10%" not in tip  # the calibrated sector is never dry


# ---------- Configurable recurring-bottleneck rule ----------


def seed_bottlenecks(db, technical: int, social: int = 0):
    sector, cell, scheme, _ = seed_report_world(db)
    for _ in range(technical):
        db.add(IrrigationClimateLog(scheme_id=scheme.id, cell_id=cell.id, operational_status="faulty", bottleneck_category="technical"))
    for _ in range(social):
        db.add(IrrigationClimateLog(scheme_id=scheme.id, cell_id=cell.id, operational_status="faulty", bottleneck_category="social"))
    db.commit()
    return scheme


def performance_row(db, scheme):
    return next(row for row in analytics.scheme_performance(db) if row["scheme_id"] == scheme.id)


def test_bottleneck_min_count_is_configurable(db, monkeypatch):
    scheme = seed_bottlenecks(db, technical=3)
    assert performance_row(db, scheme)["flagged_bottlenecks"] == ["technical"]
    monkeypatch.setattr(analytics, "get_settings", lambda: Settings(_env_file=None, bottleneck_min_count=5))
    assert performance_row(db, scheme)["flagged_bottlenecks"] == []


def test_bottleneck_window_is_configurable(db, monkeypatch):
    scheme = seed_bottlenecks(db, technical=3)
    monkeypatch.setattr(analytics, "get_settings", lambda: Settings(_env_file=None, bottleneck_window_days=30))
    # Backdate the reports beyond the window: they must drop out.
    for report in db.query(IrrigationClimateLog).all():
        report.created_at = datetime.now(timezone.utc) - timedelta(days=60)
    db.commit()
    assert performance_row(db, scheme)["flagged_bottlenecks"] == []
    assert performance_row(db, scheme)["bottleneck_window_days"] == 30


def test_bottleneck_min_share_is_configurable(db, monkeypatch):
    scheme = seed_bottlenecks(db, technical=3, social=1)  # technical = 75% of 4 reports
    assert performance_row(db, scheme)["flagged_bottlenecks"] == ["technical"]
    monkeypatch.setattr(analytics, "get_settings", lambda: Settings(_env_file=None, bottleneck_min_share=0.9))
    assert performance_row(db, scheme)["flagged_bottlenecks"] == []


def test_bottleneck_per_category_override(db, monkeypatch):
    scheme = seed_bottlenecks(db, technical=1)
    monkeypatch.setattr(analytics, "get_settings",
                        lambda: Settings(_env_file=None, bottleneck_min_count=5, bottleneck_category_min_counts="technical:1"))
    assert performance_row(db, scheme)["flagged_bottlenecks"] == ["technical"]


def test_bottleneck_flagged_only_above_historical_baseline(db):
    scheme = seed_bottlenecks(db, technical=3)
    # Three historical findings: the baseline for this category on this scheme.
    for day in (1, 2, 3):
        db.add(BottleneckBaseline(scheme_id=scheme.id, asset_name="PADAB Pumping Station 1", category="technical",
                                  finding_date=date(2023, 5, day), description="Repeated bearing failures", source="AfDB evaluation 2023"))
    db.commit()
    # At the baseline level the category is not "above" it, so nothing is flagged yet.
    row = performance_row(db, scheme)
    assert row["flagged_bottlenecks"] == [] and row["baseline_bottlenecks"] == []
    # One report above history: flagged and marked above baseline.
    db.add(IrrigationClimateLog(scheme_id=scheme.id, operational_status="faulty", bottleneck_category="technical"))
    db.commit()
    row = performance_row(db, scheme)
    assert row["flagged_bottlenecks"] == ["technical"]
    assert row["baseline_bottlenecks"] == ["technical"]


# ---------- USSD menus read from the database ----------


def test_grievance_menu_reads_database_and_paginates(db):
    sector, cell, _, user = seed_report_world(db)
    for index in range(1, 11):
        db.add(GrievanceCategory(code=f"cat_{index}", label_rw=f"Ikibazo {index}", label_en=f"Category {index}", sort_order=index))
    db.add(GrievanceCategory(code="retired", label_rw="Zimwe", label_en="Retired", sort_order=99, is_active=False))
    db.commit()

    first = ussd.handle(db, user, "5")
    assert "Category 8" in first.english and "Category 9" not in first.english
    assert "Show more" in first.english and "Retired" not in first.english
    second = ussd.handle(db, user, "5*9")
    assert "Category 9" in second.english and "Category 10" in second.english
    assert "Show more" not in second.english
    prompt = ussd.handle(db, user, "5*9*1")
    assert prompt.response.startswith("CON") and "Type your concern" in prompt.english
    done = ussd.handle(db, user, "5*9*1*Amazi ntageze ku mirima")
    assert done.response.startswith("END")
    feedback = db.query(CommunityFeedback).one()
    assert feedback.category == "Category 9" and feedback.reporter_id is None


def test_grievance_menu_falls_back_to_builtin_list(db):
    _, _, _, user = seed_report_world(db)
    db.query(GrievanceCategory).delete()
    db.commit()
    screen = ussd.handle(db, user, "5")
    assert "Input Distribution" in screen.english  # today's built-in values


def test_asset_menu_reads_database_and_links_scheme(db):
    sector, cell, scheme, user = seed_report_world(db)
    for index in range(1, 11):
        db.add(SchemeAsset(name_rw=f"Igikorwa {index}", name_en=f"Asset {index}", scheme_id=scheme.id, asset_type="pump"))
    db.add(SchemeAsset(name_rw="Igikare", name_en="Retired asset", is_active=False))
    db.commit()

    first = ussd.handle(db, user, "4")
    assert "Asset 8" in first.english and "Asset 9" not in first.english
    assert "Show more" in first.english and "Retired asset" not in first.english
    # Page 2, first asset, condition "working well" -> an irrigation report linked to the scheme.
    done = ussd.handle(db, user, "4*9*1*1")
    assert done.response.startswith("END")
    report = db.query(IrrigationClimateLog).one()
    assert report.infrastructure_name == "Asset 9" and report.scheme_id == scheme.id


def test_asset_menu_falls_back_to_builtin_inventory(db):
    _, _, _, user = seed_report_world(db)
    db.query(SchemeAsset).delete()
    db.commit()
    screen = ussd.handle(db, user, "4")
    assert "PADAB Pumping Station 1" in screen.english


# ---------- CRUD endpoints and permissions ----------


def test_category_and_asset_crud(client):
    created = client.post("/api/v1/grievance-categories", json={"label_rw": "Ibyiciro byihariye", "label_en": "Special category"})
    assert created.status_code == 201
    assert created.json()["code"] == "special_category"
    assert client.post("/api/v1/grievance-categories", json={"label_rw": "Test", "label_en": "Special category"}).status_code == 409
    category_id = created.json()["id"]
    assert client.patch(f"/api/v1/grievance-categories/{category_id}", json={"is_active": False}).json()["is_active"] is False

    schemes = client.get("/api/v1/irrigation-schemes").json()
    asset = client.post("/api/v1/scheme-assets", json={"name_rw": "Pompe 3", "name_en": "Pump 3", "scheme_id": schemes[0]["id"] if schemes else None})
    assert asset.status_code == 201
    assert client.post("/api/v1/scheme-assets", json={"name_rw": "Pompe", "name_en": "Pump 3"}).status_code == 409
    assert client.delete(f"/api/v1/scheme-assets/{asset.json()['id']}").status_code == 204
    assert client.delete(f"/api/v1/grievance-categories/{category_id}").status_code == 204


def test_category_delete_blocked_when_grievances_use_it(client):
    created = client.post("/api/v1/grievance-categories", json={"label_rw": "Amazi", "label_en": "In Use"}).json()
    client.post("/api/v1/feedback", json={"category": "In Use", "message": "the canal is blocked again"})
    assert client.delete(f"/api/v1/grievance-categories/{created['id']}").status_code == 409
    assert client.patch(f"/api/v1/grievance-categories/{created['id']}", json={"is_active": False}).status_code == 200


def test_reference_permissions(client, auth):
    monitor = auth(role="citizen_science_monitor")
    assert client.get("/api/v1/grievance-categories", headers=monitor).status_code == 403
    assert client.post("/api/v1/scheme-assets", json={"name_rw": "x", "name_en": "y"}, headers=monitor).status_code == 403
    officer = auth(role="district_officer")
    assert client.get("/api/v1/grievance-categories", headers=officer).status_code == 200
    assert client.post("/api/v1/grievance-categories", json={"label_rw": "x", "label_en": "y"}, headers=officer).status_code == 403
    admin = auth(role="administrator")
    assert client.post("/api/v1/grievance-categories", json={"label_rw": "x", "label_en": "Admin made"}, headers=admin).status_code == 201


# ---------- Import and calibration scripts ----------


def test_import_scheme_targets_refuses_rows_without_a_source():
    script = load_script("import_scheme_targets")
    rows, errors = script.parse_targets(
        "scheme,yield_target_tons,hectares,source_document,source_page\n"
        "PADAB,4120,650,Feasibility study 2023,17\n"
        "APEFA Solar,1150,, ,\n"
    )
    assert len(rows) == 1 and rows[0]["source"] == "Feasibility study 2023, p.17"
    assert len(errors) == 1 and "no source document" in errors[0] and "APEFA Solar" in errors[0]


def test_import_scheme_targets_applies_to_matched_schemes(db):
    script = load_script("import_scheme_targets")
    _, _, scheme = seed_report_world(db)[:3]
    rows, errors = script.parse_targets("scheme,yield_target_tons,hectares,source_document\n"
                                        f"{scheme.name},123.5,50,Commissioning report\n")
    assert not errors
    matched, plan_errors = script.plan(db, rows)
    assert not plan_errors and matched[0]["scheme_id"] == scheme.id
    script.apply(db, matched)
    db.refresh(scheme)
    assert scheme.baseline_yield_target_tons == 123.5
    assert scheme.baseline_source == "Commissioning report"
    assert scheme.hectares_developed == 50.0
    # A second plan now reports the current target as an update, not a first set.
    assert script.plan(db, rows)[0][0]["current_target"] == 123.5
    # An unknown scheme name is an error, never a silent skip.
    unknown, errs = script.plan(db, [{"scheme": "Nope", "yield_target_tons": 1.0, "hectares": None, "source": "doc"}])
    assert not unknown and "no irrigation scheme" in errs[0]


def test_calibrate_rolling_totals_and_percentiles():
    script = load_script("calibrate_rainfall_thresholds")
    daily = [(date(2026, 1, index), float(index)) for index in range(1, 15)]  # 1..14 mm/day
    totals = script.rolling_7day(daily)
    # The first complete window ends on day 7: days 1..7 = 28 mm.
    assert totals[0] == sum(range(1, 8)) == 28
    assert totals[-1] == sum(range(8, 15)) == 77  # days 8..14
    assert script.percentile([1, 2, 3, 4], 50) == 2.5
    dry, wet = script.propose([10.0, 20.0, 30.0, 40.0, 50.0], 20, 80)
    assert dry == 18.0 and wet == 42.0
    try:
        script.propose([10.0], 80, 20)
        raise AssertionError("wet must be above dry")
    except ValueError:
        pass


def test_calibrate_report_records_source_and_status(tmp_path):
    script = load_script("calibrate_rainfall_thresholds")
    proposals = [{
        "sector_id": 1, "sector": "Ngeruka", "source": "data/neruka.csv", "days": 365,
        "first": "2023-01-01", "last": "2023-12-31", "windows": 359, "dry_mm": 8.0, "wet_mm": 42.5,
        "previous": "environment defaults (DRY_SPELL_THRESHOLD_MM / WET_SPELL_THRESHOLD_MM)",
    }]
    report = script.build_report(proposals, 20, 80, applied=False)
    assert "Ngeruka" in report and "data/neruka.csv" in report
    assert "dry **8.0 mm**, wet **42.5 mm**" in report
    assert "proposed only" in report and "`--apply`" in report
    assert "359 complete 7-day windows" in report


def test_calibrate_reads_daily_csv(tmp_path):
    script = load_script("calibrate_rainfall_thresholds")
    csv_path = tmp_path / "rain.csv"
    csv_path.write_text("date,rainfall_mm\n2026-01-01,3\n2026-01-02,4\nnot-a-date,5\n", encoding="utf-8")
    try:
        script.load_daily(csv_path)
        raise AssertionError("bad date must raise")
    except ValueError as error:
        assert "row 4" in str(error)
    csv_path.write_text("date,rainfall_mm\n2026-01-01,3\n2026-01-02,4\n2026-01-01,1\n", encoding="utf-8")
    daily = script.load_daily(csv_path)
    assert daily == [(date(2026, 1, 1), 4.0), (date(2026, 1, 2), 4.0)]  # duplicate dates summed


def test_import_bottleneck_baseline_needs_a_source_and_deduplicates(db):
    script = load_script("import_bottleneck_baseline")
    _, _, scheme = seed_report_world(db)[:3]
    text = ("scheme,asset,category,date,description\n"
            f"{scheme.name},Pump 1,technical,2023-05-01,Bearing failures\n"
            f"{scheme.name},Pump 1,technical,2023-06-01,\n")
    rows, errors = script.parse_findings(text)  # no source column, no --source
    assert len(rows) == 0 and len(errors) == 2 and "no source" in errors[0]
    rows, errors = script.parse_findings(text, default_source="AfDB evaluation 2023")
    assert not errors and len(rows) == 2 and rows[0]["source"] == "AfDB evaluation 2023"
    matched, duplicates, plan_errors = script.plan(db, rows)
    assert not plan_errors and len(matched) == 2 and not duplicates
    script.apply(db, matched)
    # Re-planning the same rows skips them as duplicates instead of doubling the baseline.
    matched2, duplicates2, _ = script.plan(db, rows)
    assert not matched2 and len(duplicates2) == 2
    findings = db.query(BottleneckBaseline).all()
    assert len(findings) == 2 and findings[0].scheme_id == scheme.id and findings[0].finding_date == date(2023, 5, 1)
