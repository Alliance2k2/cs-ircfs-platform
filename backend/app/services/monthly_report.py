"""Monthly district report: one month of field evidence, ready to print or save as PDF.

Everything is counted inside one calendar month in Kigali time, and the headline
figures are compared with the previous month so the district can see the direction.
Only aggregates are returned: no names, phone numbers or message text.
"""
import re
from datetime import datetime, timedelta, timezone
from statistics import median

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (AdvisoryMessage, Cell, CitizenScienceLog, CommunityFeedback, FeedbackStatusEvent, IncentiveReward, IncidentCase,
                           IncidentEvent, InboundMessage, IrrigationClimateLog, IrrigationScheme, NutritionSurvey, ReportStatus, Sector, User)

KIGALI = timezone(timedelta(hours=2))
CLOSED = [ReportStatus.resolved, ReportStatus.closed]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


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
        "ussd_sessions": db.scalar(select(func.count(func.distinct(InboundMessage.session_id))).where(
            InboundMessage.channel == "ussd", InboundMessage.created_at >= start, InboundMessage.created_at < end)) or 0,
        "sms_received": count(InboundMessage, InboundMessage.channel == "sms"),
        "new_people": count(User),
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

    # Sectors reporting this month, and the busiest ones.
    activity: dict[str, int] = {}
    for model in (CitizenScienceLog, IrrigationClimateLog):
        for (cell_id,) in db.execute(select(model.cell_id).where(*in_month(model.created_at))):
            name = sector_of(cell_id) or "Location not set"
            activity[name] = activity.get(name, 0) + 1

    # Schemes: this month's evidence, scheme by scheme.
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

    # Cases: opened, resolved, and how fast.
    opened = list(db.scalars(select(IncidentCase).where(*in_month(IncidentCase.created_at))))
    first_closed = dict(db.execute(select(IncidentEvent.case_id, func.min(IncidentEvent.created_at))
                                   .where(IncidentEvent.new_status.in_(CLOSED)).group_by(IncidentEvent.case_id)).all())
    resolved_in_month = [case_id for case_id, at in first_closed.items() if start <= aware(at) < end]
    durations = [(aware(first_closed[case.id]) - aware(case.created_at)).total_seconds() / 86400 for case in opened if case.id in first_closed]
    open_at_end = db.scalar(select(func.count()).select_from(IncidentCase).where(IncidentCase.created_at < end, IncidentCase.status.not_in(CLOSED))) or 0
    by_priority: dict[str, int] = {}
    for case in opened:
        by_priority[case.priority] = by_priority.get(case.priority, 0) + 1

    # Grievances: categories, and whether the loop was closed.
    grievances = list(db.scalars(select(CommunityFeedback).where(*in_month(CommunityFeedback.created_at))))
    by_category: dict[str, int] = {}
    for item in grievances:
        by_category[item.category] = by_category.get(item.category, 0) + 1
    feedback_closed = dict(db.execute(select(FeedbackStatusEvent.feedback_id, func.min(FeedbackStatusEvent.created_at))
                                      .where(FeedbackStatusEvent.new_status.in_(CLOSED)).group_by(FeedbackStatusEvent.feedback_id)).all())
    feedback_days = [(aware(feedback_closed[item.id]) - aware(item.created_at)).total_seconds() / 86400 for item in grievances if item.id in feedback_closed]

    # Pests: what, how bad, where.
    pests: dict[str, dict] = {}
    for name, severity, cell_id in db.execute(select(CitizenScienceLog.pest_or_disease, CitizenScienceLog.severity, CitizenScienceLog.cell_id)
                                              .where(CitizenScienceLog.pest_or_disease.is_not(None), *in_month(CitizenScienceLog.created_at))):
        entry = pests.setdefault(name, {"pest": name, "reports": 0, "severe": 0, "sectors": set()})
        entry["reports"] += 1
        entry["severe"] += 1 if (severity or 0) >= 4 else 0
        if sector_of(cell_id):
            entry["sectors"].add(sector_of(cell_id))

    # Rainfall: month total per sector, averaging gauges so two gauges are not double-counted.
    gauges: dict[str, dict[int | None, float]] = {}
    readings: dict[str, int] = {}
    for reporter_id, cell_id, mm in db.execute(select(IrrigationClimateLog.reporter_id, IrrigationClimateLog.cell_id, IrrigationClimateLog.rainfall_mm)
                                               .where(IrrigationClimateLog.rainfall_mm.is_not(None), *in_month(IrrigationClimateLog.created_at))):
        name = sector_of(cell_id) or "Location not set"
        gauges.setdefault(name, {}).setdefault(reporter_id, 0.0)
        gauges[name][reporter_id] += float(mm)
        readings[name] = readings.get(name, 0) + 1
    rainfall = sorted(({"sector": name, "rainfall_mm": round(sum(totals.values()) / len(totals), 1), "gauges": len(totals), "readings": readings[name]}
                       for name, totals in gauges.items()), key=lambda row: row["rainfall_mm"])

    # Nutrition: households surveyed and the cells at highest risk.
    surveys = list(db.scalars(select(NutritionSurvey).where(*in_month(NutritionSurvey.created_at))))
    risk_by_cell: dict[int | None, list[int]] = {}
    for survey in surveys:
        risk_by_cell.setdefault(survey.cell_id, []).append(survey.stunting_risk_score)
    risk_cells = sorted(({"cell": cell_sector.get(cell_id, ("Location not set",))[0], "sector": sector_of(cell_id), "households": len(scores),
                          "average_risk": round(sum(scores) / len(scores), 1)} for cell_id, scores in risk_by_cell.items()),
                        key=lambda row: -row["average_risk"])

    # Messages and incentives sent back to citizens.
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
