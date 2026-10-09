"""Report creation and the monthly/trend reporting used by the dashboard.

The report-creation helpers are shared by the REST API, the USSD menu, and SMS keywords,
so a report from a feature phone triggers the same Act Now case rules as one entered on
the web. The monthly report and trends are built here too, entirely from aggregates.
"""
import re
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from statistics import median

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    SOURCE_CROP,
    SOURCE_INFRASTRUCTURE,
    AdvisoryMessage,
    Cell,
    CitizenScienceLog,
    CommunityFeedback,
    FeedbackStatusEvent,
    FieldUser,
    IncentiveReward,
    IncidentCase,
    IncidentEvent,
    InboundMessage,
    IrrigationClimateLog,
    IrrigationScheme,
    NutritionSurvey,
    ReportStatus,
    Sector,
)
from app.services.cases import auto_create_case
from app.services.cooperatives import participation as cooperative_participation

KIGALI = timezone(timedelta(hours=2))
CLOSED = [ReportStatus.resolved, ReportStatus.closed]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def create_crop_report(db: Session, **values) -> CitizenScienceLog:
    report = CitizenScienceLog(**values)
    db.add(report)
    db.flush()
    severity = values.get("severity")
    if severity is not None and severity >= 4:
        summary = f"{report.pest_or_disease or 'Pest or disease'} on {report.crop_type}, severity {severity}"
        auto_create_case(db, SOURCE_CROP, report, "critical" if severity == 5 else "high", summary)
    return report


def create_irrigation_report(db: Session, **values) -> IrrigationClimateLog:
    report = IrrigationClimateLog(**values)
    db.add(report)
    db.flush()
    status = values.get("operational_status")
    if status in {"faulty", "offline"}:
        summary = f"{report.infrastructure_name or 'Irrigation asset'} is {status}" + (
            f" ({report.bottleneck_category})" if report.bottleneck_category else ""
        )
        auto_create_case(db, SOURCE_INFRASTRUCTURE, report, "critical" if status == "offline" else "high", summary)
    return report


def scheme_for_cell(db: Session, cell_id: int | None) -> int | None:
    """Link a report to the scheme serving its sector, so outcomes can be verified per scheme."""
    if cell_id is None:
        return None
    cell = db.get(Cell, cell_id)
    if not cell:
        return None
    return db.scalar(
        select(IrrigationScheme.id).where(IrrigationScheme.sector_id == cell.sector_id).order_by(IrrigationScheme.id).limit(1)
    )


def scheme_by_prefix(db: Session, prefix: str) -> int | None:
    return db.scalar(select(IrrigationScheme.id).where(IrrigationScheme.name.ilike(f"{prefix}%")).order_by(IrrigationScheme.id).limit(1))


def find_or_register_user(db: Session, phone_number: str) -> FieldUser:
    """A first-time caller is registered as a farmer, keyed by phone number."""
    user = db.scalar(select(FieldUser).where(FieldUser.phone_number == phone_number))
    if user is None:
        user = FieldUser(phone_number=phone_number)
        db.add(user)
        db.flush()
    return user


def add_months(base: date, months: int) -> date:
    """Shift a date by whole calendar months, clamping the day to the month length."""
    total = base.month - 1 + months
    year, month = base.year + total // 12, total % 12 + 1
    return date(year, month, min(base.day, monthrange(year, month)[1]))


def month_window(month: str | None) -> tuple[datetime, datetime, str]:
    """'2026-10' -> (start, end) in UTC for that Kigali calendar month, and the month key."""
    if month is None:
        now = datetime.now(KIGALI)
        year, number = now.year, now.month
    else:
        match = re.fullmatch(r"(\d{4})-(\d{2})", month)
        if not match or not 1 <= int(match.group(2)) <= 12:
            raise HTTPException(status_code=422, detail="Month must look like 2026-10")
        year, number = int(match.group(1)), int(match.group(2))
    start = datetime(year, number, 1, tzinfo=KIGALI)
    end = datetime(year + (number == 12), number % 12 + 1, 1, tzinfo=KIGALI)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc), f"{year:04d}-{number:02d}"


def aware(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


def change(current: int | float, previous: int | float) -> float | None:
    return round((current - previous) / previous * 100) if previous else None


def headline(db: Session, start: datetime, end: datetime) -> dict:
    def count(model, *conditions):
        return db.scalar(select(func.count()).select_from(model).where(model.created_at >= start, model.created_at < end, *conditions)) or 0

    crop = count(CitizenScienceLog)
    water = count(IrrigationClimateLog)
    return {
        "reports": crop + water,
        "harvest_reports": count(CitizenScienceLog, CitizenScienceLog.pest_or_disease.is_(None)),
        "pest_reports": count(CitizenScienceLog, CitizenScienceLog.pest_or_disease.is_not(None)),
        "rain_readings": count(IrrigationClimateLog, IrrigationClimateLog.rainfall_mm.is_not(None)),
        "asset_faults": count(IrrigationClimateLog, IrrigationClimateLog.operational_status.in_(["faulty", "offline"])),
        "grievances": count(CommunityFeedback),
        "nutrition_surveys": count(NutritionSurvey),
        "ussd_sessions": db.scalar(
            select(func.count(func.distinct(InboundMessage.session_id))).where(
                InboundMessage.channel == "ussd", InboundMessage.created_at >= start, InboundMessage.created_at < end
            )
        )
        or 0,
        "sms_received": count(InboundMessage, InboundMessage.channel == "sms"),
        "new_people": count(FieldUser),
        "cases_opened": count(IncidentCase),
    }


def build_monthly_report(db: Session, month: str | None = None) -> dict:
    start, end, key = month_window(month)
    previous_start, _, previous_key = month_window((start.astimezone(KIGALI) - timedelta(days=1)).strftime("%Y-%m"))
    in_month = lambda column: (column >= start, column < end)  # noqa: E731

    now_figures = headline(db, start, end)
    before = headline(db, previous_start, start)
    figures = {name: {"value": value, "previous": before[name], "change_percent": change(value, before[name])} for name, value in now_figures.items()}

    sectors = {sector.id: sector.name for sector in db.scalars(select(Sector))}
    cell_sector = {cell.id: (cell.name, cell.sector_id) for cell in db.scalars(select(Cell))}
    sector_of = lambda cell_id: sectors.get(cell_sector.get(cell_id, (None, None))[1]) if cell_id else None  # noqa: E731

    activity: dict[str, int] = {}
    for model in (CitizenScienceLog, IrrigationClimateLog):
        for (cell_id,) in db.execute(select(model.cell_id).where(*in_month(model.created_at))):
            name = sector_of(cell_id) or "Location not set"
            activity[name] = activity.get(name, 0) + 1

    schemes = []
    for scheme in db.scalars(select(IrrigationScheme).order_by(IrrigationScheme.name)):
        crop_rows = db.execute(select(CitizenScienceLog.expected_harvest_tons, CitizenScienceLog.reported_harvest_tons, CitizenScienceLog.severity)
                               .where(CitizenScienceLog.scheme_id == scheme.id, *in_month(CitizenScienceLog.created_at))).all()
        water = db.execute(select(IrrigationClimateLog.operational_status, IrrigationClimateLog.bottleneck_category)
                           .where(IrrigationClimateLog.scheme_id == scheme.id, *in_month(IrrigationClimateLog.created_at))).all()
        bottlenecks: dict[str, int] = {}
        for status, category in water:
            if status in ("faulty", "offline") and category:
                bottlenecks[category] = bottlenecks.get(category, 0) + 1
        schemes.append({
            "name": scheme.name, "is_active": scheme.is_active, "target_tons": scheme.baseline_yield_target_tons, "target_source": scheme.baseline_source,
            "crop_reports": len(crop_rows),
            "expected_tons": round(sum(row[0] or 0 for row in crop_rows), 2), "reported_tons": round(sum(row[1] or 0 for row in crop_rows), 2),
            "severe_pest_reports": sum(1 for row in crop_rows if (row[2] or 0) >= 4),
            "asset_faults": sum(1 for status, _ in water if status in ("faulty", "offline")),
            "bottlenecks": dict(sorted(bottlenecks.items(), key=lambda pair: -pair[1])),
            "grievances": db.scalar(select(func.count()).select_from(CommunityFeedback).where(CommunityFeedback.scheme_id == scheme.id, *in_month(CommunityFeedback.created_at))) or 0,
        })

    opened = list(db.scalars(select(IncidentCase).where(*in_month(IncidentCase.created_at))))
    first_closed = dict(db.execute(select(IncidentEvent.case_id, func.min(IncidentEvent.created_at))
                                   .where(IncidentEvent.new_status.in_(CLOSED)).group_by(IncidentEvent.case_id)).all())
    resolved_in_month = [case_id for case_id, at in first_closed.items() if start <= aware(at) < end]
    durations = [(aware(first_closed[case.id]) - aware(case.created_at)).total_seconds() / 86400 for case in opened if case.id in first_closed]
    open_at_end = db.scalar(select(func.count()).select_from(IncidentCase).where(IncidentCase.created_at < end, IncidentCase.status.not_in(CLOSED))) or 0
    by_priority: dict[str, int] = {}
    for case in opened:
        by_priority[case.priority] = by_priority.get(case.priority, 0) + 1

    grievances = list(db.scalars(select(CommunityFeedback).where(*in_month(CommunityFeedback.created_at))))
    by_category: dict[str, int] = {}
    for item in grievances:
        by_category[item.category] = by_category.get(item.category, 0) + 1
    feedback_closed = dict(db.execute(select(FeedbackStatusEvent.feedback_id, func.min(FeedbackStatusEvent.created_at))
                                      .where(FeedbackStatusEvent.new_status.in_(CLOSED)).group_by(FeedbackStatusEvent.feedback_id)).all())
    feedback_days = [(aware(feedback_closed[item.id]) - aware(item.created_at)).total_seconds() / 86400 for item in grievances if item.id in feedback_closed]

    pests: dict[str, dict] = {}
    for name, severity, cell_id in db.execute(select(CitizenScienceLog.pest_or_disease, CitizenScienceLog.severity, CitizenScienceLog.cell_id)
                                              .where(CitizenScienceLog.pest_or_disease.is_not(None), *in_month(CitizenScienceLog.created_at))):
        entry = pests.setdefault(name, {"pest": name, "reports": 0, "severe": 0, "sectors": set()})
        entry["reports"] += 1
        entry["severe"] += 1 if (severity or 0) >= 4 else 0
        if sector_of(cell_id):
            entry["sectors"].add(sector_of(cell_id))

    gauges: dict[str, dict[int | None, float]] = {}
    readings: dict[str, int] = {}
    for reporter_id, cell_id, mm in db.execute(select(IrrigationClimateLog.reporter_id, IrrigationClimateLog.cell_id, IrrigationClimateLog.rainfall_mm)
                                               .where(IrrigationClimateLog.rainfall_mm.is_not(None), *in_month(IrrigationClimateLog.created_at))):
        name = sector_of(cell_id) or "Location not set"
        gauge = (reporter_id, cell_id if reporter_id is None else None)
        gauges.setdefault(name, {}).setdefault(gauge, 0.0)
        gauges[name][gauge] += float(mm)
        readings[name] = readings.get(name, 0) + 1
    rainfall = sorted(({"sector": name, "rainfall_mm": round(sum(totals.values()) / len(totals), 1), "gauges": len(totals), "readings": readings[name]}
                       for name, totals in gauges.items()), key=lambda row: row["rainfall_mm"])

    surveys = list(db.scalars(select(NutritionSurvey).where(*in_month(NutritionSurvey.created_at))))
    risk_by_cell: dict[int | None, list[int]] = {}
    for survey in surveys:
        risk_by_cell.setdefault(survey.cell_id, []).append(survey.stunting_risk_score)
    risk_cells = sorted(({"cell": cell_sector.get(cell_id, ("Location not set",))[0], "sector": sector_of(cell_id), "households": len(scores),
                          "average_risk": round(sum(scores) / len(scores), 1)} for cell_id, scores in risk_by_cell.items()),
                        key=lambda row: -row["average_risk"])

    sms_out: dict[str, int] = {}
    for purpose, status, total in db.execute(select(AdvisoryMessage.purpose, AdvisoryMessage.status, func.count())
                                             .where(*in_month(AdvisoryMessage.created_at)).group_by(AdvisoryMessage.purpose, AdvisoryMessage.status)):
        sms_out[purpose or "other"] = sms_out.get(purpose or "other", 0) + total
    delivery: dict[str, int] = dict(db.execute(select(AdvisoryMessage.status, func.count()).where(*in_month(AdvisoryMessage.created_at))
                                               .group_by(AdvisoryMessage.status)).all())
    rewards = db.execute(select(func.count(), func.coalesce(func.sum(IncentiveReward.amount_rwf), 0))
                         .where(IncentiveReward.status.in_(["sent", "dry_run"]), *in_month(IncentiveReward.created_at))).one()

    start_kigali = start.astimezone(KIGALI)
    return {
        "month": key, "label": f"{MONTHS[start_kigali.month - 1]} {start_kigali.year}", "previous_month": previous_key,
        "generated_at": datetime.now(timezone.utc),
        "figures": figures,
        "sectors_reporting": len([name for name in activity if name != "Location not set"]), "sectors_total": len(sectors),
        "sector_activity": [{"sector": name, "reports": total} for name, total in sorted(activity.items(), key=lambda pair: -pair[1])],
        "schemes": schemes,
        # Cooperative participation this month, ranked for the Inteko z'Abaturage meeting (WP5).
        "cooperatives": [
            {**row, "sector": sectors.get(row["sector_id"]) if row["sector_id"] else None}
            for row in sorted(cooperative_participation(db, start, end), key=lambda row: (-row["reports_total"], -row["active_reporters"], row["name"]))
        ],
        "cases": {"opened": len(opened), "by_priority": by_priority, "resolved_in_month": len(resolved_in_month), "open_at_month_end": open_at_end,
                  "median_days_to_resolve": round(median(durations), 1) if durations else None},
        "grievances": {"received": len(grievances), "by_category": dict(sorted(by_category.items(), key=lambda pair: -pair[1])),
                       "resolved": sum(1 for item in grievances if item.status in CLOSED),
                       "median_days_to_resolve": round(median(feedback_days), 1) if feedback_days else None,
                       "close_loop_sms": sms_out.get("close_loop", 0)},
        "pests": sorted(({**entry, "sectors": sorted(entry["sectors"])} for entry in pests.values()), key=lambda row: (-row["severe"], -row["reports"])),
        "rainfall": rainfall,
        "nutrition": {"households": len(surveys), "average_risk": round(sum(s.stunting_risk_score for s in surveys) / len(surveys), 1) if surveys else None,
                      "high_risk_households": sum(1 for s in surveys if s.stunting_risk_score >= 4), "cells": risk_cells[:8]},
        "messages": {"sms_sent_by_purpose": dict(sorted(sms_out.items(), key=lambda pair: -pair[1])), "delivery": delivery,
                     "airtime_rewards": rewards[0], "airtime_rwf": int(rewards[1])},
    }


def build_trends(db: Session, months: int = 12) -> dict:
    """Month-by-month series for the dashboard trend charts, oldest first (Kigali months)."""
    months = max(2, min(months, 36))
    current = datetime.now(KIGALI)
    keys = []
    year, number = current.year, current.month
    for _ in range(months):
        keys.append(f"{year:04d}-{number:02d}")
        year, number = (year - 1, 12) if number == 1 else (year, number - 1)
    keys.reverse()
    start, _, _ = month_window(keys[0])
    month_of = lambda value: aware(value).astimezone(KIGALI).strftime("%Y-%m")  # noqa: E731
    rows = {key: {"month": key, "label": f"{MONTHS[int(key[5:]) - 1][:3]} {key[:4]}", "reports": 0, "severe_pests": 0, "rain_readings": 0,
                  "asset_faults": 0, "grievances": 0, "cases_opened": 0, "cases_resolved": 0, "expected_tons": 0.0, "reported_tons": 0.0,
                  "plantings": 0, "households": 0, "average_risk": None, "rainfall_mm": None} for key in keys}

    def bucket(value):
        return rows.get(month_of(value)) if value is not None else None

    for created, severity, expected, reported, planted in db.execute(select(CitizenScienceLog.created_at, CitizenScienceLog.severity,
                                                                   CitizenScienceLog.expected_harvest_tons, CitizenScienceLog.reported_harvest_tons,
                                                                   CitizenScienceLog.planting_date)
                                                            .where(CitizenScienceLog.created_at >= start)):
        row = bucket(created)
        if row:
            row["reports"] += 1
            row["severe_pests"] += 1 if (severity or 0) >= 4 else 0
            row["expected_tons"] += expected or 0
            row["reported_tons"] += reported or 0
            if planted is not None:
                row["plantings"] += 1
    gauges: dict[str, dict] = {}
    for created, status, mm, reporter_id, cell_id in db.execute(select(IrrigationClimateLog.created_at, IrrigationClimateLog.operational_status,
                                                                       IrrigationClimateLog.rainfall_mm, IrrigationClimateLog.reporter_id, IrrigationClimateLog.cell_id)
                                                       .where(IrrigationClimateLog.created_at >= start)):
        row = bucket(created)
        if not row:
            continue
        row["reports"] += 1
        row["asset_faults"] += 1 if status in ("faulty", "offline") else 0
        if mm is not None:
            row["rain_readings"] += 1
            gauge = (reporter_id, cell_id if reporter_id is None else None)
            gauges.setdefault(row["month"], {}).setdefault(gauge, 0.0)
            gauges[row["month"]][gauge] += float(mm)
    for key, totals in gauges.items():
        rows[key]["rainfall_mm"] = round(sum(totals.values()) / len(totals), 1)
    for (created,) in db.execute(select(CommunityFeedback.created_at).where(CommunityFeedback.created_at >= start)):
        if row := bucket(created):
            row["grievances"] += 1
    for (created,) in db.execute(select(IncidentCase.created_at).where(IncidentCase.created_at >= start)):
        if row := bucket(created):
            row["cases_opened"] += 1
    for _, closed in db.execute(select(IncidentEvent.case_id, func.min(IncidentEvent.created_at)).where(IncidentEvent.new_status.in_(CLOSED))
                                .group_by(IncidentEvent.case_id)):
        if row := bucket(closed):
            row["cases_resolved"] += 1
    risks: dict[str, list[int]] = {}
    for created, score in db.execute(select(NutritionSurvey.created_at, NutritionSurvey.stunting_risk_score).where(NutritionSurvey.created_at >= start)):
        if row := bucket(created):
            row["households"] += 1
            risks.setdefault(row["month"], []).append(score)
    for key, scores in risks.items():
        rows[key]["average_risk"] = round(sum(scores) / len(scores), 1)
    for row in rows.values():
        row["expected_tons"] = round(row["expected_tons"], 1)
        row["reported_tons"] = round(row["reported_tons"], 1)
    return {"months": [rows[key] for key in keys]}
