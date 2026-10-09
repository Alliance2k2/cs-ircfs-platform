"""Dashboard analytics: every query and calculation the planner dashboard needs.

Route handlers stay thin; all SQL and aggregation lives here.
"""
from datetime import datetime, timedelta, timezone
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells
from app.core.security import Principal
from app.core.config import get_settings
from app.db.models import (
    SOURCE_INFRASTRUCTURE,
    AdvisoryMessage,
    BottleneckBaseline,
    Cell,
    CitizenScienceLog,
    CommunityFeedback,
    FeedbackStatusEvent,
    FieldUser,
    IncidentCase,
    IncentiveReward,
    InboundMessage,
    IrrigationClimateLog,
    IrrigationScheme,
    NutritionSurvey,
    ReportStatus,
    ORIGIN_SIMULATOR,
    UserRole,
)
from app.schemas import ActNowItem, DashboardSummary
from app.services.advisory import advice_for_rainfall, threshold_map
from app.services.cases import case_source
from app.services.evidence import counted

CLOSED = [ReportStatus.resolved, ReportStatus.closed]
ACTIVE = [ReportStatus.open, ReportStatus.triaged, ReportStatus.assigned, ReportStatus.in_progress]
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2}


def bottleneck_rule(settings=None):
    """The recurring-bottleneck rule (WP7): (window_days, min_count, min_share, per-category counts).

    Defaults come from BOTTLENECK_* settings; an imported AfDB baseline further
    requires a category's count to be above its historical findings.
    """
    settings = settings or get_settings()
    return (
        max(1, settings.bottleneck_window_days),
        max(1, settings.bottleneck_min_count),
        max(0.0, settings.bottleneck_min_share),
        settings.bottleneck_category_counts,
    )


def aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive timestamps; treat them as UTC so durations work on both databases."""
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


def dashboard_summary(db: Session, principal: Principal) -> DashboardSummary:
    count = lambda query: db.scalar(query) or 0  # noqa: E731
    crop_reports = count(select(func.count()).select_from(CitizenScienceLog))
    irrigation_reports = count(select(func.count()).select_from(IrrigationClimateLog))
    return DashboardSummary(
        registered_farmers=count(select(func.count()).select_from(FieldUser).where(FieldUser.role == UserRole.farmer)),
        total_reports=crop_reports + irrigation_reports,
        active_schemes=count(select(func.count()).select_from(IrrigationScheme).where(IrrigationScheme.is_active.is_(True))),
        open_complaints=count(select(func.count()).select_from(CommunityFeedback).where(CommunityFeedback.status.not_in(CLOSED))),
        faulty_or_offline_assets=count(select(func.count()).select_from(IrrigationClimateLog).where(IrrigationClimateLog.operational_status.in_(["faulty", "offline"]))),
        households_surveyed=count(select(func.count()).select_from(NutritionSurvey)),
        average_stunting_risk=round(float(db.scalar(select(func.avg(NutritionSurvey.stunting_risk_score))) or 0), 1) or None,
        rewards_paid_rwf=count(select(func.sum(IncentiveReward.amount_rwf)).where(IncentiveReward.status.in_(["sent", "dry_run"]))),
        field_messages=count(select(func.count()).select_from(InboundMessage)),
    )


def farmer_summary(db: Session) -> DashboardSummary:
    farmers = db.scalar(select(func.count()).select_from(FieldUser).where(FieldUser.role == UserRole.farmer, FieldUser.is_active.is_(True))) or 0
    crop_reports = db.scalar(select(func.count()).select_from(CitizenScienceLog)) or 0
    irrigation_reports = db.scalar(select(func.count()).select_from(IrrigationClimateLog)) or 0
    return DashboardSummary(registered_farmers=farmers, total_reports=crop_reports + irrigation_reports, active_schemes=0, open_complaints=0, faulty_or_offline_assets=0)


def act_now_queue(db: Session, principal: Principal) -> list[ActNowItem]:
    items: list[ActNowItem] = []
    cells = allowed_cells(db, principal)
    for case in db.scalars(select(IncidentCase).where(IncidentCase.status.in_(ACTIVE))):
        report = case_source(db, case)
        if report is None or report.data_origin == ORIGIN_SIMULATOR:  # simulator tests are not work to do
            continue
        if case.source_type == SOURCE_INFRASTRUCTURE:
            title = f"{report.infrastructure_name or 'Irrigation asset'} is {report.operational_status}"
            details = report.fault_description or report.bottleneck_category
            item_type = "infrastructure"
        else:
            title = f"{report.pest_or_disease or 'Crop risk'} reported for {report.crop_type}"
            details = report.notes
            item_type = "pest_or_disease"
        items.append(ActNowItem(item_type=item_type, item_id=case.id, priority=case.priority, title=title, status=case.status.value,
                                scheme_id=report.scheme_id, cell_id=report.cell_id, created_at=case.created_at,
                                assigned_to_account_id=case.assigned_to_account_id, due_at=case.due_at, details=details))
    for feedback in db.scalars(select(CommunityFeedback).where(CommunityFeedback.status.in_(ACTIVE), counted(CommunityFeedback))):
        items.append(ActNowItem(item_type="community_feedback", item_id=feedback.id, priority="medium", title=feedback.category,
                                status=feedback.status.value, scheme_id=feedback.scheme_id, cell_id=feedback.cell_id,
                                created_at=feedback.created_at, assigned_to_field_user_id=feedback.assigned_to_field_user_id,
                                due_at=feedback.due_at, details=feedback.message))
    if cells is not None:
        items = [item for item in items if item.cell_id in cells]
    return sorted(items, key=lambda item: (PRIORITY_ORDER.get(item.priority, 3), aware(item.created_at)))


def scheme_performance(db: Session) -> list[dict]:
    """Objective 1 (outcome verification) and Objective 2 (bottleneck detection), scheme by scheme."""
    window_days, min_count, min_share, category_counts = bottleneck_rule()
    window_start = datetime.now(timezone.utc) - timedelta(days=window_days)
    # Historical AfDB findings (WP7): a category is only flagged above its baseline.
    baselines: dict[int, dict[str, int]] = {}
    for scheme_id, category, findings in db.execute(
        select(BottleneckBaseline.scheme_id, BottleneckBaseline.category, func.count()).group_by(
            BottleneckBaseline.scheme_id, BottleneckBaseline.category
        )
    ).all():
        baselines.setdefault(scheme_id, {})[category] = findings
    results = []
    for scheme in db.scalars(select(IrrigationScheme).order_by(IrrigationScheme.name)):
        expected, reported, crop_reports = db.execute(
            select(func.sum(CitizenScienceLog.expected_harvest_tons), func.sum(CitizenScienceLog.reported_harvest_tons), func.count(CitizenScienceLog.id))
            .where(CitizenScienceLog.scheme_id == scheme.id)
        ).one()
        pest_alerts = db.scalar(select(func.count()).select_from(CitizenScienceLog).where(CitizenScienceLog.scheme_id == scheme.id, CitizenScienceLog.severity >= 4)) or 0
        faults = db.scalar(select(func.count()).select_from(IrrigationClimateLog).where(IrrigationClimateLog.scheme_id == scheme.id, IrrigationClimateLog.operational_status.in_(["faulty", "offline"]))) or 0
        grievances = db.scalar(select(func.count()).select_from(CommunityFeedback).where(CommunityFeedback.scheme_id == scheme.id, CommunityFeedback.status.not_in(CLOSED))) or 0
        window_reports = db.scalar(select(func.count()).select_from(IrrigationClimateLog).where(IrrigationClimateLog.scheme_id == scheme.id, IrrigationClimateLog.created_at >= window_start)) or 0
        bottlenecks = dict(db.execute(
            select(IrrigationClimateLog.bottleneck_category, func.count())
            .where(IrrigationClimateLog.scheme_id == scheme.id, IrrigationClimateLog.bottleneck_category.is_not(None), IrrigationClimateLog.created_at >= window_start)
            .group_by(IrrigationClimateLog.bottleneck_category)
        ).all())
        scheme_baselines = baselines.get(scheme.id, {})

        def flagged(category: str, count: int) -> bool:
            needed = category_counts.get(category, min_count)
            if count < needed:
                return False
            if min_share and window_reports and count / window_reports < min_share:
                return False
            baseline = scheme_baselines.get(category)
            return baseline is None or count > baseline  # above the historical baseline

        above_baseline = sorted(category for category, count in bottlenecks.items()
                                if scheme_baselines.get(category) is not None and count > scheme_baselines[category])
        basis, achieved = ("reported", reported) if reported else ("forecast", expected)
        target = scheme.baseline_yield_target_tons
        percent = round(achieved / target * 100, 1) if target and achieved is not None else None
        status = "no_target" if not target else "no_data" if percent is None else "on_track" if percent >= 90 else "watch" if percent >= 60 else "below_target"
        # Yield forecaster inputs (WP1): when the crop reports say harvest is expected.
        # Grouped in Python so the query stays portable across SQLite and PostgreSQL.
        harvest_by_month: dict[str, float] = {}
        for month_value, tons in db.execute(
            select(CitizenScienceLog.expected_harvest_month, CitizenScienceLog.expected_harvest_tons)
            .where(CitizenScienceLog.scheme_id == scheme.id, CitizenScienceLog.expected_harvest_month.is_not(None))
        ).all():
            key = month_value.strftime("%Y-%m")
            harvest_by_month[key] = harvest_by_month.get(key, 0.0) + (tons or 0)
        harvest_calendar = [{"month": month, "tons": round(total, 2)} for month, total in sorted(harvest_by_month.items())]
        results.append({
            "scheme_id": scheme.id, "name": scheme.name, "is_active": scheme.is_active, "implementing_partner": scheme.implementing_partner,
            "hectares_developed": scheme.hectares_developed, "target_tons": target, "target_source": scheme.baseline_source,
            "expected_tons": round(expected or 0, 2), "reported_tons": round(reported or 0, 2), "basis": basis, "achievement_percent": percent,
            "status": status, "crop_reports": crop_reports, "pest_alerts": pest_alerts, "infrastructure_faults": faults, "open_grievances": grievances,
            "bottlenecks": bottlenecks, "flagged_bottlenecks": sorted(category for category, n in bottlenecks.items() if flagged(category, n)),
            "baseline_bottlenecks": above_baseline, "bottleneck_window_days": window_days,
            "harvest_calendar": harvest_calendar,
        })
    return results


def response_health(db: Session) -> dict:
    """Module 3 accountability: how fast community concerns are resolved and communicated back."""
    feedback = list(db.scalars(select(CommunityFeedback)))
    resolved = [item for item in feedback if item.status in CLOSED]
    first_resolution = dict(db.execute(
        select(FeedbackStatusEvent.feedback_id, func.min(FeedbackStatusEvent.created_at))
        .where(FeedbackStatusEvent.new_status.in_(CLOSED)).group_by(FeedbackStatusEvent.feedback_id)
    ).all())
    durations = [(aware(first_resolution[item.id]) - aware(item.created_at)).total_seconds() / 86400 for item in resolved if item.id in first_resolution]
    cases = list(db.scalars(select(IncidentCase)))
    cases_resolved = [case for case in cases if case.status in CLOSED]
    close_loop_messages = db.scalar(select(func.count()).select_from(AdvisoryMessage).where(AdvisoryMessage.purpose == "close_loop")) or 0
    by_category: dict[str, int] = {}
    for item in feedback:
        by_category[item.category] = by_category.get(item.category, 0) + 1
    return {
        "feedback_total": len(feedback), "feedback_resolved": len(resolved), "feedback_open": len(feedback) - len(resolved),
        "resolution_rate": round(len(resolved) / len(feedback) * 100) if feedback else None,
        "median_days_to_resolve": round(median(durations), 1) if durations else None,
        "cases_total": len(cases), "cases_resolved": len(cases_resolved),
        "cases_notified": sum(1 for case in cases if case.reporter_notified_at), "close_loop_messages": close_loop_messages,
        "by_category": dict(sorted(by_category.items(), key=lambda pair: -pair[1])),
    }


def report_position(report, cells: dict[int, Cell]) -> tuple[float, float] | None:
    if report.latitude is not None and report.longitude is not None:
        return report.latitude, report.longitude
    cell = cells.get(report.cell_id)
    if cell and cell.latitude is not None and cell.longitude is not None:
        return cell.latitude, cell.longitude
    return None


def pest_heatmap(db: Session, days: int = 90) -> list[dict]:
    """SMS/USSD pest and disease alerts as weighted points for the heatmap layer."""
    cells = {cell.id: cell for cell in db.scalars(select(Cell))}
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    points = []
    for report in db.scalars(select(CitizenScienceLog).where(CitizenScienceLog.pest_or_disease.is_not(None), CitizenScienceLog.created_at >= cutoff,
                                                             counted(CitizenScienceLog))):
        position = report_position(report, cells)
        if position:
            points.append({"latitude": position[0], "longitude": position[1], "weight": round((report.severity or 3) / 5, 2),
                           "pest": report.pest_or_disease, "crop": report.crop_type, "severity": report.severity})
    return points


def rainfall_map(db: Session, days: int = 7) -> list[dict]:
    """Citizen-Led Rain Gauge Network: 7-day rainfall per cell and its drought-warning level."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    thresholds = threshold_map(db)
    rows = db.execute(
        select(Cell.id, Cell.name, Cell.latitude, Cell.longitude, Cell.sector_id, func.sum(IrrigationClimateLog.rainfall_mm), func.count(IrrigationClimateLog.id))
        .join(IrrigationClimateLog, IrrigationClimateLog.cell_id == Cell.id)
        .where(IrrigationClimateLog.rainfall_mm.is_not(None), IrrigationClimateLog.created_at >= cutoff, counted(IrrigationClimateLog))
        .group_by(Cell.id, Cell.name, Cell.latitude, Cell.longitude, Cell.sector_id)
    ).all()
    return [{"cell_id": cell_id, "cell": name, "latitude": lat, "longitude": lng, "rainfall_mm": round(total or 0, 1), "readings": readings,
             "level": advice_for_rainfall(total, readings, thresholds.get(sector_id)).level}
            for cell_id, name, lat, lng, sector_id, total, readings in rows if lat is not None and lng is not None]


DOWN = ("faulty", "offline")


def latest_asset_status(db: Session, cells: set[int] | None = None, scheme_id: int | None = None) -> list[dict]:
    """The most recent condition report for each named asset of each scheme.

    "Assets down" means the latest report says faulty or offline. Counting every fault
    report ever received (the legacy summary figure) overstates current problems once an
    asset is repaired and reported working again.
    """
    query = (select(IrrigationClimateLog).where(IrrigationClimateLog.infrastructure_name.is_not(None),
                                                IrrigationClimateLog.operational_status.is_not(None), counted(IrrigationClimateLog))
             .order_by(IrrigationClimateLog.created_at, IrrigationClimateLog.id))
    if cells is not None:
        query = query.where(IrrigationClimateLog.cell_id.in_(cells))
    if scheme_id is not None:
        query = query.where(IrrigationClimateLog.scheme_id == scheme_id)
    latest: dict[tuple, IrrigationClimateLog] = {}
    for report in db.scalars(query):
        latest[(report.scheme_id, report.infrastructure_name.strip().lower())] = report
    return [{"asset": report.infrastructure_name, "scheme_id": report.scheme_id, "status": report.operational_status,
             "down": report.operational_status in DOWN, "bottleneck": report.bottleneck_category, "description": report.fault_description,
             "cell_id": report.cell_id, "reported_at": report.created_at}
            for report in sorted(latest.values(), key=lambda item: (item.operational_status not in DOWN, item.infrastructure_name))]


def nutrition_summary(db: Session) -> dict:
    """Household Nutrition Tracker: stunting-risk drivers by cell."""
    surveys = list(db.scalars(select(NutritionSurvey)))
    cells = {cell.id: cell for cell in db.scalars(select(Cell))}
    by_cell: dict[int | None, list[NutritionSurvey]] = {}
    for survey in surveys:
        by_cell.setdefault(survey.cell_id, []).append(survey)
    rows = []
    for cell_id, items in by_cell.items():
        cell = cells.get(cell_id)
        rows.append({"cell_id": cell_id, "cell": cell.name if cell else "Unknown cell", "latitude": cell.latitude if cell else None,
                     "longitude": cell.longitude if cell else None, "households": len(items),
                     "average_risk": round(sum(s.stunting_risk_score for s in items) / len(items), 1),
                     "high_risk": sum(1 for s in items if s.stunting_risk_score >= 4)})
    total = len(surveys)
    return {
        "households": total,
        "average_risk": round(sum(s.stunting_risk_score for s in surveys) / total, 1) if total else None,
        "high_risk_households": sum(1 for s in surveys if s.stunting_risk_score >= 4),
        "one_meal_households": sum(1 for s in surveys if s.meals_per_day == 1),
        "food_insufficient": sum(1 for s in surveys if not s.food_sufficient),
        "by_cell": sorted(rows, key=lambda row: -row["average_risk"]),
    }
