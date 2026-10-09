"""Executive overview: the District Planning Dashboard's first screen.

Every headline figure is a *metric envelope* that carries its own meaning, so the
dashboard never shows a bare number::

    {"key", "label", "value", "unit", "period", "definition", "source", "note"}

``source`` says how far a figure can be trusted:

* ``live_unverified`` — citizen reports as received; not individually verified,
* ``platform`` — the platform's own workflow records (cases, grievances),
* ``documented`` — a value entered with its source document (scheme targets),
* ``demo`` — the database holds demonstration data (scripts/seed_demo_data.py),
* ``missing`` — not enough evidence to state a value; ``note`` says why.

Simulator tests never count. No trend arrows or growth rates are produced: the
platform has no validated baseline period to compare against yet.
"""
from datetime import datetime, timedelta, timezone
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.privacy import sees_personal_data
from app.core.scope import allowed_cells, cell_filter
from app.core.security import Principal
from app.db.models import (
    Cell,
    CitizenScienceLog,
    CommunityFeedback,
    IncidentCase,
    IncidentEvent,
    IrrigationClimateLog,
    IrrigationScheme,
    Sector,
)
from app.services.advisory import sector_schedule
from app.services.analytics import ACTIVE, CLOSED, act_now_queue, aware, latest_asset_status
from app.services.cases import case_source
from app.services.evidence import counted, demo_mode

LIVE, PLATFORM, DOCUMENTED, DEMO, MISSING = "live_unverified", "platform", "documented", "demo", "missing"
YIELD_NOT_COMPARABLE = ("Not calculated. Citizen harvest reports come from a sample of farmers, while the scheme target "
                        "covers the whole scheme; a comparable achievement needs harvested area, crop and season on each "
                        "report and a target for the same crop, area and season.")


def metric(key: str, label: str, value, unit: str, period: str, definition: str, source: str, note: str | None = None) -> dict:
    return {"key": key, "label": label, "value": value, "unit": unit, "period": period, "definition": definition,
            "source": MISSING if value is None else source, "note": note}


def overview(db: Session, principal: Principal, days: int = 30, scheme_id: int | None = None, sector_id: int | None = None) -> dict:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    period = f"Last {days} days"
    evidence = DEMO if demo_mode(db) else LIVE

    cells = allowed_cells(db, principal)
    if sector_id is not None:
        sector_cells = set(db.scalars(select(Cell.id).where(Cell.sector_id == sector_id)))
        cells = sector_cells if cells is None else cells & sector_cells

    def scope(model, since: datetime | None = start):
        conditions = [counted(model), cell_filter(model.cell_id, cells)]
        if scheme_id is not None:
            conditions.append(model.scheme_id == scheme_id)
        if since is not None:
            conditions.append(model.created_at >= since)
        return conditions

    def count(model, *extra) -> int:
        return db.scalar(select(func.count()).select_from(model).where(*scope(model), *extra)) or 0

    # --- Citizen reporting ---------------------------------------------------------
    crop_reports, water_reports = count(CitizenScienceLog), count(IrrigationClimateLog)
    reporters = set(db.scalars(select(CitizenScienceLog.reporter_id).where(*scope(CitizenScienceLog), CitizenScienceLog.reporter_id.is_not(None))))
    reporters |= set(db.scalars(select(IrrigationClimateLog.reporter_id).where(*scope(IrrigationClimateLog), IrrigationClimateLog.reporter_id.is_not(None))))

    reporting_sectors: set[int] = set()
    for model in (CitizenScienceLog, IrrigationClimateLog):
        reporting_sectors |= set(db.scalars(select(Cell.sector_id).join(model, model.cell_id == Cell.id).where(*scope(model)).distinct()))
    total_sectors = 1 if sector_id is not None else (db.scalar(select(func.count()).select_from(Sector)) or 0)
    if sector_id is not None:
        reporting_sectors &= {sector_id}

    # --- Cases and grievances (current state, not limited to the period) -----------
    open_cases = []
    for case in db.scalars(select(IncidentCase).where(IncidentCase.status.in_(ACTIVE))):
        report = case_source(db, case)
        if report is None or not in_scope(report, cells, scheme_id):
            continue
        open_cases.append(case)
    open_grievances = db.scalar(select(func.count()).select_from(CommunityFeedback)
                                .where(*scope(CommunityFeedback, since=None), CommunityFeedback.status.in_(ACTIVE))) or 0

    period_cases = []
    for case in db.scalars(select(IncidentCase).where(IncidentCase.created_at >= start)):
        report = case_source(db, case)
        if report is not None and in_scope(report, cells, scheme_id):
            period_cases.append(case)
    resolved_at = dict(db.execute(select(IncidentEvent.case_id, func.min(IncidentEvent.created_at))
                                  .where(IncidentEvent.new_status.in_(CLOSED)).group_by(IncidentEvent.case_id)).all())
    durations = [(aware(resolved_at[case.id]) - aware(case.created_at)).total_seconds() / 86400
                 for case in period_cases if case.status in CLOSED and case.id in resolved_at]

    # --- Infrastructure, rainfall ---------------------------------------------------
    assets = latest_asset_status(db, cells, scheme_id)
    assets_down = [asset for asset in assets if asset["down"]]
    schedule = [row for row in sector_schedule(db) if sector_id is None or row["sector_id"] == sector_id]
    gauged = [row["rainfall_mm_7d"] for row in schedule if row["readings"]]

    metrics = [
        metric("citizen_reports", "Citizen reports", crop_reports + water_reports, "reports", period,
               "Crop, pest, rainfall and infrastructure reports received by USSD, SMS or staff entry. Each is counted as received; "
               "reports are not individually verified.", evidence),
        metric("active_reporters", "Active reporters", len(reporters), "people", period,
               "Registered phones that sent at least one crop, pest, rainfall or infrastructure report.", evidence),
        metric("reporting_coverage", "Sectors reporting", round(len(reporting_sectors) / total_sectors * 100) if total_sectors else None, "%", period,
               "Share of sectors with at least one report. Low coverage means district figures rest on few places.", evidence,
               f"{len(reporting_sectors)} of {total_sectors} sector{'s' if total_sectors != 1 else ''}"),
        metric("critical_incidents", "Critical incidents", sum(1 for case in open_cases if case.priority == "critical"), "open cases", "Now",
               "Open cases from offline assets or severity-5 pest reports, which the platform marks critical.", PLATFORM),
        metric("open_actions", "Open actions", len(open_cases) + open_grievances, "items", "Now",
               "Open incident cases plus grievances not yet resolved.", PLATFORM,
               f"{len(open_cases)} case{'s' if len(open_cases) != 1 else ''}, {open_grievances} grievance{'s' if open_grievances != 1 else ''}"),
        metric("assets_down", "Assets down", len(assets_down) if assets else None, "assets", "Latest report per asset",
               "Named irrigation assets whose most recent condition report says faulty or offline.", evidence,
               f"of {len(assets)} asset{'s' if len(assets) != 1 else ''} with a condition report" if assets else "No asset condition reports yet"),
        metric("rainfall_7d", "Rainfall, 7 days", round(sum(gauged) / len(gauged), 1) if gauged else None, "mm", "Last 7 days",
               "Average across sectors of each sector's citizen rain-gauge total. Gauges are not calibrated instruments.", evidence,
               f"{len(gauged)} sector{'s' if len(gauged) != 1 else ''} with gauge readings" if gauged else "No rain-gauge readings in the last 7 days"),
        metric("median_days_to_resolve", "Median days to resolve", round(median(durations), 1) if durations else None, "days", period,
               "For cases opened in the period and already resolved: days from opening to the first resolution.", PLATFORM,
               f"{len(durations)} of {len(period_cases)} case{'s' if len(period_cases) != 1 else ''} opened in the period resolved" if period_cases else "No cases opened in the period"),
    ]

    return {
        "generated_at": now,
        "period": {"days": days, "start": start, "end": now},
        "filters": {"scheme_id": scheme_id, "sector_id": sector_id},
        "demo_mode": evidence == DEMO,
        "metrics": metrics,
        "schemes": scheme_rows(db, scope, assets, scheme_id, evidence, period),
        "assets": assets,
        "rainfall": [{"sector_id": row["sector_id"], "sector": row["sector"], "rainfall_mm_7d": row["rainfall_mm_7d"] if row["readings"] else None,
                      "readings": row["readings"], "forecast_mm_7d": row["forecast_mm_7d"], "level": row["level"], "advice": row["message_en"],
                      "threshold_source": row["threshold_source"]} for row in schedule],
        # The Act Now queue is district staff work; monitors follow the figures only.
        "priority_actions": priority_actions(db, principal, cells, scheme_id) if sees_personal_data(principal) else None,
        "recent_reports": recent_reports(db, scope),
    }


def in_scope(report, cells: set[int] | None, scheme_id: int | None) -> bool:
    if report.data_origin == "simulator":
        return False
    if cells is not None and report.cell_id not in cells:
        return False
    return scheme_id is None or report.scheme_id == scheme_id


def scheme_rows(db: Session, scope, assets: list[dict], scheme_id: int | None, evidence: str, period: str) -> list[dict]:
    query = select(IrrigationScheme).where(IrrigationScheme.is_active.is_(True)).order_by(IrrigationScheme.name)
    if scheme_id is not None:
        query = select(IrrigationScheme).where(IrrigationScheme.id == scheme_id)
    rows = []
    for scheme in db.scalars(query):
        def count(model, *extra) -> int:
            return db.scalar(select(func.count()).select_from(model).where(*scope(model), model.scheme_id == scheme.id, *extra)) or 0

        reported = db.scalar(select(func.sum(CitizenScienceLog.reported_harvest_tons))
                             .where(*scope(CitizenScienceLog), CitizenScienceLog.scheme_id == scheme.id)) or 0
        scheme_assets = [asset for asset in assets if asset["scheme_id"] == scheme.id]
        target_note = f"Source: {scheme.baseline_source}" if scheme.baseline_source else "No documented target entered yet"
        rows.append({
            "scheme_id": scheme.id, "name": scheme.name, "implementing_partner": scheme.implementing_partner,
            "hectares_developed": scheme.hectares_developed,
            "reports": count(CitizenScienceLog) + count(IrrigationClimateLog),
            "pest_alerts": count(CitizenScienceLog, CitizenScienceLog.severity >= 4),
            "fault_reports": count(IrrigationClimateLog, IrrigationClimateLog.operational_status.in_(("faulty", "offline"))),
            "assets_down": sum(1 for asset in scheme_assets if asset["down"]),
            "assets_reported": len(scheme_assets),
            "open_grievances": db.scalar(select(func.count()).select_from(CommunityFeedback)
                                         .where(*scope(CommunityFeedback, since=None), CommunityFeedback.scheme_id == scheme.id,
                                                CommunityFeedback.status.in_(ACTIVE))) or 0,
            "reported_harvest": metric("reported_harvest", "Reported harvest", round(reported, 1), "t", period,
                                       "Sum of harvests reported by citizens in the period. A sample of farmers, not the scheme's total output.", evidence),
            "yield_target": metric("yield_target", "Yield target", scheme.baseline_yield_target_tons if scheme.baseline_source else None, "t",
                                   "As documented", "The scheme's yield target as entered with its source document.", DOCUMENTED, target_note),
            "yield_achievement": metric("yield_achievement", "Yield achievement", None, "%", period,
                                        "100 × verified observed yield ÷ verified target yield, for the same crop, area and season.", MISSING,
                                        YIELD_NOT_COMPARABLE),
        })
    return rows


def priority_actions(db: Session, principal: Principal, cells: set[int] | None, scheme_id: int | None, limit: int = 8) -> list[dict]:
    items = [item for item in act_now_queue(db, principal)
             if (cells is None or item.cell_id in cells) and (scheme_id is None or item.scheme_id == scheme_id)]
    names = dict(db.execute(select(Cell.id, Sector.name).join(Sector, Sector.id == Cell.sector_id)).all())
    return [{"item_type": item.item_type, "item_id": item.item_id, "priority": item.priority, "title": item.title, "status": item.status,
             "sector": names.get(item.cell_id), "scheme_id": item.scheme_id, "created_at": item.created_at, "due_at": item.due_at,
             "assigned": item.assigned_to_account_id is not None or item.assigned_to_field_user_id is not None}
            for item in items[:limit]]


def recent_reports(db: Session, scope, limit: int = 8) -> list[dict]:
    """The latest reports as one-line summaries: no names, phone numbers or message text."""
    names = dict(db.execute(select(Cell.id, Sector.name).join(Sector, Sector.id == Cell.sector_id)).all())
    items = []
    for log in db.scalars(select(CitizenScienceLog).where(*scope(CitizenScienceLog, since=None)).order_by(CitizenScienceLog.created_at.desc()).limit(limit)):
        kind, label = (("pest", f"{log.pest_or_disease} on {log.crop_type}, severity {log.severity}") if log.pest_or_disease
                       else ("harvest", f"{log.crop_type} harvest report"))
        items.append({"kind": kind, "label": label, "sector": names.get(log.cell_id), "created_at": log.created_at, "origin": log.data_origin})
    for log in db.scalars(select(IrrigationClimateLog).where(*scope(IrrigationClimateLog, since=None)).order_by(IrrigationClimateLog.created_at.desc()).limit(limit)):
        if log.rainfall_mm is not None:
            kind, label = "rain", f"Rain gauge: {log.rainfall_mm:g} mm"
        elif log.operational_status in ("faulty", "offline"):
            kind, label = "fault", f"{log.infrastructure_name or 'Irrigation asset'} {log.operational_status}"
        else:
            kind, label = "water", f"{log.infrastructure_name or 'Irrigation asset'} checked: {log.operational_status or 'reported'}"
        items.append({"kind": kind, "label": label, "sector": names.get(log.cell_id), "created_at": log.created_at, "origin": log.data_origin})
    items.sort(key=lambda item: aware(item["created_at"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return items[:limit]
