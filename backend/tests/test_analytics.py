"""Dashboard analytics: summaries, scheme performance, bottlenecks, and response health."""
from app.core.security import Principal
from app.db.models import (
    Cell,
    CitizenScienceLog,
    CommunityFeedback,
    FieldUser,
    IrrigationClimateLog,
    IrrigationScheme,
    NutritionSurvey,
    ReportStatus,
    Sector,
    UserRole,
)
from app.services import analytics

ADMIN = Principal(name="test", role=UserRole.administrator)


def world(db):
    """A scheme with one crop report, one rainfall reading, a grievance, and a survey."""
    sector = Sector(name="Ngeruka")
    db.add(sector)
    db.flush()
    cell = Cell(name="Gihembe", sector_id=sector.id)
    db.add(cell)
    db.flush()
    scheme = IrrigationScheme(name="APEFA Solar", sector_id=sector.id, baseline_yield_target_tons=10.0, baseline_source="test")
    db.add(scheme)
    db.flush()
    db.add(FieldUser(phone_number="+250788000001", role=UserRole.farmer, cell_id=cell.id))
    db.add(CitizenScienceLog(scheme_id=scheme.id, cell_id=cell.id, crop_type="Maize", expected_harvest_tons=8.0))
    db.add(IrrigationClimateLog(scheme_id=scheme.id, cell_id=cell.id, rainfall_mm=12.0))
    db.add(CommunityFeedback(cell_id=cell.id, category="Water", message="blocked"))
    db.add(NutritionSurvey(cell_id=cell.id, meals_per_day=1, ate_protein_or_vegetables=False, food_sufficient=False, stunting_risk_score=5))
    db.commit()
    return sector, cell, scheme


def test_dashboard_summary_counts_known_records(db):
    world(db)
    summary = analytics.dashboard_summary(db, ADMIN)
    assert summary.registered_farmers == 1
    assert summary.total_reports == 2
    assert summary.active_schemes == 1
    assert summary.open_complaints == 1
    assert summary.households_surveyed == 1
    assert summary.average_stunting_risk == 5.0


def test_scheme_performance_achievement_percent(db):
    _, _, scheme = world(db)
    row = next(r for r in analytics.scheme_performance(db) if r["scheme_id"] == scheme.id)
    assert row["achievement_percent"] == 80.0
    assert row["basis"] == "forecast"
    assert row["status"] == "watch"


def test_scheme_performance_groups_expected_harvest_by_month(db):
    """WP1: the expected-harvest calendar buckets tons per month, in order."""
    from datetime import date

    _, _, scheme = world(db)
    db.add(CitizenScienceLog(scheme_id=scheme.id, crop_type="Maize", expected_harvest_tons=2.0,
                             expected_harvest_month=date(2027, 3, 10)))
    db.add(CitizenScienceLog(scheme_id=scheme.id, crop_type="Rice", expected_harvest_tons=3.5,
                             expected_harvest_month=date(2027, 3, 1)))
    db.add(CitizenScienceLog(scheme_id=scheme.id, crop_type="Beans", expected_harvest_tons=1.0,
                             expected_harvest_month=date(2027, 5, 1)))
    db.commit()
    row = next(r for r in analytics.scheme_performance(db) if r["scheme_id"] == scheme.id)
    assert row["harvest_calendar"] == [
        {"month": "2027-03", "tons": 5.5},
        {"month": "2027-05", "tons": 1.0},
    ]


def test_scheme_performance_harvest_calendar_empty_without_dates(db):
    _, _, scheme = world(db)
    row = next(r for r in analytics.scheme_performance(db) if r["scheme_id"] == scheme.id)
    assert row["harvest_calendar"] == []


def test_bottleneck_flagged_when_reported_three_times(db):
    _, cell, scheme = world(db)
    for _ in range(3):
        db.add(IrrigationClimateLog(scheme_id=scheme.id, cell_id=cell.id, operational_status="faulty", bottleneck_category="technical"))
    db.commit()
    row = next(r for r in analytics.scheme_performance(db) if r["scheme_id"] == scheme.id)
    assert row["flagged_bottlenecks"] == ["technical"]


def test_bottleneck_not_flagged_below_threshold(db):
    _, cell, scheme = world(db)
    for _ in range(2):
        db.add(IrrigationClimateLog(scheme_id=scheme.id, cell_id=cell.id, operational_status="faulty", bottleneck_category="technical"))
    db.commit()
    row = next(r for r in analytics.scheme_performance(db) if r["scheme_id"] == scheme.id)
    assert row["flagged_bottlenecks"] == []


def test_response_health_resolution_rate_is_correct(db):
    _, cell, _ = world(db)
    db.add(CommunityFeedback(cell_id=cell.id, category="Water", message="a second concern", status=ReportStatus.resolved))
    db.commit()
    health = analytics.response_health(db)
    assert health["feedback_total"] == 2
    assert health["feedback_resolved"] == 1
    assert health["resolution_rate"] == 50
