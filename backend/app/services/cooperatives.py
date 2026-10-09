"""Cooperative participation and training progress (WP5, Section 8).

The monthly Inteko z'Abaturage meeting needs a ranking of how active each
cooperative's members are; the pilot needs a progress bar towards the target
of trained Citizen Science Monitors. Everything here counts real records:
crop/pest reports, rainfall and infrastructure reports, and nutrition surveys
filed by the cooperative's member field users.

Windows are Africa/Kigali calendar days and months, consistent with the
monthly report. This module must not import ``app.services.reporting``:
the monthly report calls ``participation()`` here.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.scope import cell_filter
from app.db.models import (
    CitizenScienceLog,
    Cooperative,
    FieldUser,
    IrrigationClimateLog,
    NutritionSurvey,
    UserRole,
)

KIGALI = ZoneInfo("Africa/Kigali")
REPORT_MODELS = ((CitizenScienceLog, "crop"), (IrrigationClimateLog, "irrigation"), (NutritionSurvey, "nutrition"))


def _members(db: Session, cells: set[int] | None) -> dict[int, list[int]]:
    """cooperative_id -> member field-user ids (area-scoped)."""
    query = select(FieldUser.cooperative_id, FieldUser.id).where(FieldUser.cooperative_id.is_not(None))
    query = query.where(cell_filter(FieldUser.cell_id, cells))
    members: dict[int, list[int]] = {}
    for cooperative_id, field_user_id in db.execute(query):
        members.setdefault(cooperative_id, []).append(field_user_id)
    return members


def _last_reports(db: Session, members: dict[int, list[int]]) -> dict[int, datetime | None]:
    """cooperative_id -> most recent report date from any member, all time."""
    reporter_last: dict[int, datetime | None] = {}
    for model, _ in REPORT_MODELS:
        for reporter_id, last_at in db.execute(select(model.reporter_id, func.max(model.created_at)).where(model.reporter_id.is_not(None)).group_by(model.reporter_id)):
            previous = reporter_last.get(reporter_id)
            if last_at is not None and last_at.tzinfo is None:
                last_at = last_at.replace(tzinfo=timezone.utc)
            if previous is None or (last_at is not None and last_at > previous):
                reporter_last[reporter_id] = last_at
    result: dict[int, datetime | None] = {}
    for cooperative_id, ids in members.items():
        dates = [reporter_last[reporter_id] for reporter_id in ids if reporter_last.get(reporter_id) is not None]
        result[cooperative_id] = max(dates) if dates else None
    return result


def _window_counts(db: Session, members: dict[int, list[int]], start: datetime, end: datetime | None) -> dict[int, dict]:
    """Report counts per cooperative in [start, end): by type plus distinct active reporters."""
    counts: dict[int, dict] = {cooperative_id: {"crop": 0, "irrigation": 0, "nutrition": 0, "active": set()} for cooperative_id in members}
    reporter_cooperative = {reporter_id: cooperative_id for cooperative_id, ids in members.items() for reporter_id in ids}
    if not reporter_cooperative:
        return counts
    for model, kind in REPORT_MODELS:
        query = select(model.reporter_id, func.count()).where(model.reporter_id.in_(list(reporter_cooperative)), model.created_at >= start)
        if end is not None:
            query = query.where(model.created_at < end)
        for reporter_id, total in db.execute(query.group_by(model.reporter_id)):
            entry = counts[reporter_cooperative[reporter_id]]
            entry[kind] += total
            entry["active"].add(reporter_id)
    return counts


def participation(
    db: Session,
    start: datetime,
    end: datetime | None = None,
    *,
    cells: set[int] | None = None,
    sector_ids: frozenset[int] | list[int] | None = None,
    members: dict[int, list[int]] | None = None,
    last_reports: dict[int, datetime | None] | None = None,
) -> list[dict]:
    """One row per cooperative with member counts and reports inside the window.

    ``members`` and ``last_reports`` are computed once and reused when the caller
    needs several windows (the endpoint shows 30 days and month-to-date).
    """
    query = select(Cooperative)
    if sector_ids is not None:
        # Area-level access: a cooperative belongs to its sector; no sector means
        # the cooperative is only visible district-wide.
        query = query.where(Cooperative.sector_id.in_(sector_ids))
    cooperatives = list(db.scalars(query.order_by(Cooperative.name)))
    if members is None:
        members = _members(db, cells)
    if last_reports is None:
        last_reports = _last_reports(db, members)
    counts = _window_counts(db, members, start, end)
    rows = []
    for cooperative in cooperatives:
        member_ids = members.get(cooperative.id, [])
        entry = counts.get(cooperative.id, {"crop": 0, "irrigation": 0, "nutrition": 0, "active": set()})
        champions = db.scalar(
            select(func.count()).select_from(FieldUser).where(FieldUser.cooperative_id == cooperative.id, FieldUser.is_data_champion.is_(True))
        ) or 0
        rows.append(
            {
                "id": cooperative.id,
                "name": cooperative.name,
                "sector_id": cooperative.sector_id,
                "is_pilot": cooperative.is_pilot,
                "members": len(member_ids),
                "data_champions": champions,
                "crop_reports": entry["crop"],
                "irrigation_reports": entry["irrigation"],
                "nutrition_surveys": entry["nutrition"],
                "reports_total": entry["crop"] + entry["irrigation"] + entry["nutrition"],
                "active_reporters": len(entry["active"]),
                "last_report_at": last_reports.get(cooperative.id),
            }
        )
    return rows


def ranking(db: Session, days: int = 30, *, cells: set[int] | None = None, sector_ids: frozenset[int] | list[int] | None = None) -> list[dict]:
    """Participation rows for the Inteko z'Abaturage ranking: last 30 days and
    month to date, sorted by 30-day reports (then month-to-date, then name)."""
    now = datetime.now(timezone.utc)
    month_start = datetime.now(KIGALI).replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    shared_members = _members(db, cells)
    shared_last = _last_reports(db, shared_members)
    window_start = now - timedelta(days=days)
    in_window = participation(db, window_start, now, cells=cells, sector_ids=sector_ids, members=shared_members, last_reports=shared_last)
    in_month = participation(db, month_start, now, cells=cells, sector_ids=sector_ids, members=shared_members, last_reports=shared_last)
    month_by_id = {row["id"]: row for row in in_month}
    rows = []
    for row in in_window:
        month_row = month_by_id[row["id"]]
        rows.append(
            {
                **row,
                "reports_mtd": month_row["reports_total"],
                "crop_reports_30d": row["crop_reports"],
                "irrigation_reports_30d": row["irrigation_reports"],
                "nutrition_surveys_30d": row["nutrition_surveys"],
                "active_reporters_30d": row["active_reporters"],
                "reports_30d": row["reports_total"],
            }
        )
    rows.sort(key=lambda row: (-row["reports_30d"], -row["reports_mtd"], row["name"]))
    return rows


def training_progress(db: Session, *, cells: set[int] | None = None) -> dict:
    """Trained Citizen Science Monitors against MONITOR_TRAINING_TARGET, plus
    Data Champion and pilot-cooperative counts."""
    settings = get_settings()
    scope = cell_filter(FieldUser.cell_id, cells)
    monitors = db.scalar(select(func.count()).select_from(FieldUser).where(FieldUser.role == UserRole.citizen_science_monitor, scope)) or 0
    trained = db.scalar(
        select(func.count()).select_from(FieldUser).where(
            FieldUser.role == UserRole.citizen_science_monitor, FieldUser.trained_at.is_not(None), scope
        )
    ) or 0
    champions = db.scalar(select(func.count()).select_from(FieldUser).where(FieldUser.is_data_champion.is_(True), scope)) or 0
    pilots = db.scalar(select(func.count()).select_from(Cooperative).where(Cooperative.is_pilot.is_(True))) or 0
    trained_on = db.scalar(select(func.max(FieldUser.trained_at)).where(FieldUser.trained_at.is_not(None), scope))
    target = settings.monitor_training_target
    return {
        "trained_monitors": trained,
        "target": target,
        "percent": round(trained / target * 100, 1) if target else 0.0,
        "monitors_total": monitors,
        "data_champions": champions,
        "pilot_cooperatives": pilots,
        "pilot_target": settings.pilot_cooperative_target,
        "trained_on": trained_on,
    }
