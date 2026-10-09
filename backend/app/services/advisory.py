"""Irrigation Scheduling Assistant, Local Insights tips, nutrition scoring, and airtime incentives."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    AdviceRun,
    AdvisoryThreshold,
    Cell,
    FieldUser,
    IncentiveReward,
    IrrigationClimateLog,
    NutritionSurvey,
    Sector,
    UserRole,
)
from app.services.evidence import counted
from app.services.forecast import rainfall_forecast
from app.services.sms import deliver, send_airtime

KIGALI = timezone(timedelta(hours=2))
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
ADVICE_PURPOSE = "irrigation_schedule"


@dataclass
class IrrigationAdvice:
    level: str
    rainfall_mm: float | None
    readings: int
    message_rw: str
    message_en: str


def advice_for_rainfall(total_mm: float | None, readings: int, thresholds: tuple[float, float] | None = None) -> IrrigationAdvice:
    """Translate 7-day rainfall into irrigation advice.

    ``thresholds`` is an optional (dry, wet) pair from ``advisory_thresholds`` for one
    sector; without it the configured DRY_SPELL_THRESHOLD_MM / WET_SPELL_THRESHOLD_MM apply.
    """
    settings = get_settings()
    dry_mm, wet_mm = thresholds or (settings.dry_spell_threshold_mm, settings.wet_spell_threshold_mm)
    if not readings:
        return IrrigationAdvice("no_data", None, 0,
                                "Nta makuru y'imvura aheruka. Abafite ibipimo by'imvura, nimutwoherereze ibipimo.",
                                "No recent rainfall readings. Rain-gauge holders, please send today's reading.")
    mm = round(total_mm or 0.0, 1)
    if mm < dry_mm:
        return IrrigationAdvice("irrigate_more", mm, readings,
                                f"Inama: imvura yabaye nke ({mm} mm mu minsi 7). Ongera kuhira ho 10% muri iki cyumweru.",
                                f"Rainfall was low ({mm} mm in 7 days). Increase irrigation cycles by 10% this week.")
    if mm > wet_mm:
        return IrrigationAdvice("irrigate_less", mm, readings,
                                f"Inama: imvura ihagije ({mm} mm mu minsi 7). Gabanya kuhira kugira ngo muzigame amazi.",
                                f"Rainfall is sufficient ({mm} mm in 7 days). Reduce irrigation to conserve water.")
    return IrrigationAdvice("normal", mm, readings,
                            f"Inama: imvura isanzwe ({mm} mm mu minsi 7). Komeza gahunda isanzwe yo kuhira.",
                            f"Rainfall is normal ({mm} mm in 7 days). Keep the usual irrigation schedule.")


def with_forecast(advice: IrrigationAdvice, forecast_mm: float | None, dry_mm: float | None = None) -> IrrigationAdvice:
    """Add a look-ahead note when the 7-day forecast changes what a farmer should do."""
    if forecast_mm is None:
        return advice
    settings = get_settings()
    dry = settings.dry_spell_threshold_mm if dry_mm is None else dry_mm
    f = forecast_mm
    if advice.level == "irrigate_more" and f >= 2 * dry:
        # A dry week followed by heavy forecast rain: one clear action instead of "irrigate more, but…".
        mm = advice.rainfall_mm
        return IrrigationAdvice("normal", mm, advice.readings,
                                f"Inama: imvura yabaye nke ({mm} mm mu minsi 7), ariko imvura ya {f} mm iteganyijwe mu minsi 7 iri imbere. "
                                "Komeza gahunda isanzwe, mwongere murebe nyuma y'iminsi 2-3.",
                                f"Rainfall was low ({mm} mm in 7 days), but {f} mm is forecast for the next 7 days. "
                                "Keep the usual schedule and check again in 2-3 days.")
    notes = {
        "normal": (f < 2, " Nta mvura iteganyijwe mu minsi 7 iri imbere: mwitegure kongera kuhira.",
                   " No rain is forecast for the next 7 days: be ready to irrigate more."),
        "irrigate_less": (f < 2, " Imvura nke iteganyijwe mu minsi 7 iri imbere: muzasubire kuri gahunda isanzwe vuba.",
                   " Little rain is forecast for the next 7 days: return to the usual schedule soon."),
        "no_data": (True, f" Iteganyagihe: imvura ya {f} mm mu minsi 7 iri imbere.", f" Forecast: {f} mm of rain in the next 7 days."),
    }
    applies, rw, en = notes.get(advice.level, (False, "", ""))
    if not applies:
        return advice
    return IrrigationAdvice(advice.level, advice.rainfall_mm, advice.readings, advice.message_rw + rw, advice.message_en + en)


def rainfall_by_sector(db: Session, days: int = 7) -> dict[int, tuple[float, int]]:
    """Return {sector_id: (total_mm, readings)} for citizen rain-gauge readings in the window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(Cell.sector_id, IrrigationClimateLog.reporter_id, IrrigationClimateLog.cell_id, IrrigationClimateLog.rainfall_mm)
        .join(Cell, Cell.id == IrrigationClimateLog.cell_id)
        .where(IrrigationClimateLog.rainfall_mm.is_not(None), IrrigationClimateLog.created_at >= cutoff, counted(IrrigationClimateLog))
    ).all()
    # Sum each gauge (reporter, or cell when anonymous) over the window, then average the
    # gauges in a sector so two gauges reading the same rain are not double-counted.
    gauges: dict[int, dict[tuple, float]] = {}
    readings: dict[int, int] = {}
    for sector_id, reporter_id, cell_id, mm in rows:
        key = (reporter_id, cell_id if reporter_id is None else None)
        gauges.setdefault(sector_id, {}).setdefault(key, 0.0)
        gauges[sector_id][key] += float(mm)
        readings[sector_id] = readings.get(sector_id, 0) + 1
    return {sector_id: (sum(totals.values()) / len(totals), readings[sector_id]) for sector_id, totals in gauges.items()}


def threshold_rows(db: Session) -> list[AdvisoryThreshold]:
    """Calibrated per-sector thresholds from ``advisory_thresholds`` (WP7)."""
    return list(db.scalars(select(AdvisoryThreshold)))


def threshold_map(db: Session) -> dict[int, tuple[float, float]]:
    """Calibrated per-sector (dry, wet) thresholds. Sectors without a calibrated
    row fall back to the environment defaults."""
    return {row.sector_id: (row.dry_mm, row.wet_mm) for row in threshold_rows(db)}


def sector_schedule(db: Session) -> list[dict]:
    rainfall = rainfall_by_sector(db)
    sectors = db.scalars(select(Sector).order_by(Sector.name)).all()
    forecast = rainfall_forecast({s.id: (s.latitude, s.longitude) for s in sectors if s.latitude is not None and s.longitude is not None})
    calibrated_rows = threshold_rows(db)
    thresholds = {row.sector_id: (row.dry_mm, row.wet_mm) for row in calibrated_rows}
    sources = {row.sector_id: row.source for row in calibrated_rows}
    settings = get_settings()
    rows = []
    for sector in sectors:
        total, readings = rainfall.get(sector.id, (None, 0))
        calibrated = thresholds.get(sector.id)
        advice = with_forecast(advice_for_rainfall(total, readings, calibrated), forecast.get(sector.id),
                               calibrated[0] if calibrated else None)
        rows.append({"sector_id": sector.id, "sector": sector.name, "level": advice.level, "rainfall_mm_7d": advice.rainfall_mm,
                     "forecast_mm_7d": forecast.get(sector.id), "readings": advice.readings, "message_rw": advice.message_rw, "message_en": advice.message_en,
                     "threshold_dry_mm": calibrated[0] if calibrated else settings.dry_spell_threshold_mm,
                     "threshold_wet_mm": calibrated[1] if calibrated else settings.wet_spell_threshold_mm,
                     "threshold_source": sources.get(sector.id),
                     "latitude": sector.latitude, "longitude": sector.longitude})
    return rows


def sector_recipients(db: Session, sector_id: int) -> list[tuple[str, int | None]]:
    """Phones in a sector that receive advice: leaders, monitors, and farmers."""
    return db.execute(
        select(FieldUser.phone_number, FieldUser.cell_id).join(Cell, Cell.id == FieldUser.cell_id)
        .where(Cell.sector_id == sector_id, FieldUser.is_active.is_(True),
               FieldUser.role.in_([UserRole.cooperative_leader, UserRole.citizen_science_monitor, UserRole.farmer]))
    ).all()


def broadcast_advice(db: Session, rows: list[dict], preview: bool = False) -> list[dict]:
    """SMS each sector's advice to its field users. The caller commits when not previewing."""
    sent = []
    for row in rows:
        recipients = sector_recipients(db, row["sector_id"])
        if not preview:
            for phone, cell_id in recipients:
                deliver(db, phone, row["message_rw"], purpose=ADVICE_PURPOSE, cell_id=cell_id)
        sent.append({"sector": row["sector"], "level": row["level"], "recipients": len(recipients),
                     "message_rw": row["message_rw"], "message_en": row["message_en"]})
    return sent


def current_week_key(now: datetime | None = None) -> str:
    """Monday of the current week in Africa/Kigali, e.g. '2026-10-05'. Idempotency key."""
    local = (now or datetime.now(timezone.utc)).astimezone(KIGALI)
    return (local.date() - timedelta(days=local.weekday())).isoformat()


def next_advice_run(settings=None, now: datetime | None = None) -> datetime | None:
    """Next scheduled automatic send in Africa/Kigali, or None when the scheduler is off."""
    settings = settings or get_settings()
    if not settings.advice_schedule_enabled:
        return None
    weekday = settings.advice_schedule_weekday.strip().lower()[:3]
    target = WEEKDAYS.index(weekday) if weekday in WEEKDAYS else 0
    try:
        hour, minute = (int(part) for part in settings.advice_schedule_time.split(":", 1))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        hour, minute = 6, 0
    local = (now or datetime.now(timezone.utc)).astimezone(KIGALI)
    run = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    run += timedelta(days=(target - local.weekday()) % 7)
    if run <= local:
        run += timedelta(days=7)
    return run


def _aggregate_status(statuses: list[str]) -> str:
    if not statuses:
        return "dry_run"
    if all(status == "sent" for status in statuses):
        return "sent"
    if all(status == "dry_run" for status in statuses):
        return "dry_run"
    if all(status == "failed" for status in statuses):
        return "failed"
    return "partial"


def send_weekly_advice(db: Session, preview: bool = False) -> dict:
    """Send this week's irrigation advice once per sector (WP2).

    Sectors that already received this week's advice are skipped, so running the script
    twice — or the script and the in-process scheduler overlapping — never duplicates a
    send. Sectors without rain-gauge readings are never included.
    """
    settings = get_settings()
    week_key = current_week_key()
    schedule = sector_schedule(db)
    rows = [row for row in schedule if row["level"] != "no_data"]
    sectors, skipped = [], 0
    for row in rows:
        run = db.scalar(select(AdviceRun).where(AdviceRun.week_key == week_key, AdviceRun.sector_id == row["sector_id"]))
        if run is not None:
            skipped += 1
            continue
        recipients = sector_recipients(db, row["sector_id"])
        if preview:
            sectors.append({"sector": row["sector"], "recipients": len(recipients), "status": "preview"})
            continue
        if not recipients:
            continue  # nobody to send to yet; try again next run rather than locking the sector out
        statuses = []
        for phone, cell_id in recipients:
            record = deliver(db, phone, row["message_rw"], purpose=ADVICE_PURPOSE, cell_id=cell_id)
            statuses.append(record.status)
        status = _aggregate_status(statuses)
        db.add(AdviceRun(week_key=week_key, sector_id=row["sector_id"], recipients=len(recipients), status=status))
        sectors.append({"sector": row["sector"], "recipients": len(recipients), "status": status})
    if not preview:
        db.commit()
    return {
        "week_key": week_key, "preview": preview, "sectors": sectors,
        "skipped_already_sent": skipped,
        "no_readings": sum(1 for row in schedule if row["level"] == "no_data"),
        "total_recipients": sum(item["recipients"] for item in sectors),
        "dry_run": settings.sms_provider != "africas_talking",
    }


def weekly_advice_status(db: Session) -> dict:
    """What advice.html shows: the last automatic send and the next scheduled run."""
    settings = get_settings()
    latest = db.scalar(select(AdviceRun).order_by(AdviceRun.created_at.desc(), AdviceRun.id.desc()).limit(1))
    last = None
    if latest is not None:
        totals = db.execute(select(func.count(), func.coalesce(func.sum(AdviceRun.recipients), 0))
                            .where(AdviceRun.week_key == latest.week_key)).one()
        last = {"week_key": latest.week_key, "sent_at": latest.created_at, "sectors": totals[0], "recipients": totals[1]}
    upcoming = next_advice_run(settings)
    return {
        "enabled": settings.advice_schedule_enabled,
        "weekday": settings.advice_schedule_weekday,
        "time": settings.advice_schedule_time,
        "timezone": "Africa/Kigali",
        "week_key": current_week_key(),
        "last_run": last,
        "next_run": upcoming,
    }


def local_tip(db: Session, user: FieldUser) -> str:
    """'Local Insights' reply (architecture Section 8.3): give value back after every report."""
    sector_id = db.scalar(select(Cell.sector_id).where(Cell.id == user.cell_id)) if user.cell_id else None
    rainfall = rainfall_by_sector(db)
    if sector_id is not None:
        total, readings = rainfall.get(sector_id, (None, 0))
        return advice_for_rainfall(total, readings, threshold_map(db).get(sector_id)).message_rw
    values = list(rainfall.values())
    total, readings = (sum(v[0] for v in values) / len(values), sum(v[1] for v in values)) if values else (None, 0)
    return advice_for_rainfall(total, readings).message_rw


def nutrition_risk_score(meals_per_day: int, ate_protein_or_vegetables: bool, food_sufficient: bool) -> int:
    """1 (low risk) to 5 (high risk): fewer meals, no protein/vegetables, and food shortage add risk."""
    score = 1 + {1: 2, 2: 1}.get(meals_per_day, 0)
    score += 0 if ate_protein_or_vegetables else 1
    score += 0 if food_sufficient else 1
    return min(score, 5)


def incentivised_report_count(db: Session, user: FieldUser) -> int:
    """How many of the user's reports count towards a reward (settings: INCENTIVE_REPORT_TYPES)."""
    types = get_settings().incentive_types
    count = 0
    irrigation_conditions = []
    if "rainfall" in types:
        irrigation_conditions.append(IrrigationClimateLog.rainfall_mm.is_not(None))
    if "infrastructure" in types:
        irrigation_conditions.append(IrrigationClimateLog.operational_status.is_not(None))
    if irrigation_conditions:
        count += db.scalar(select(func.count()).select_from(IrrigationClimateLog)
                           .where(IrrigationClimateLog.reporter_id == user.id, or_(*irrigation_conditions))) or 0
    if "nutrition" in types:
        count += db.scalar(select(func.count()).select_from(NutritionSurvey)
                           .where(NutritionSurvey.reporter_id == user.id)) or 0
    return count


def nutrition_rewards_this_month(db: Session, user: FieldUser) -> int:
    """Rewards already paid to this household for a nutrition survey in the current Kigali month."""
    month_start = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=2))).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(select(func.count()).select_from(IncentiveReward).where(
        IncentiveReward.field_user_id == user.id,
        IncentiveReward.reason.like("%nutrition survey%"),
        IncentiveReward.created_at >= month_start.astimezone(timezone.utc),
    )) or 0


def maybe_reward(db: Session, user: FieldUser, from_nutrition_survey: bool = False) -> IncentiveReward | None:
    """Every Nth incentivised report earns an airtime micro-bonus (Section 8.1).

    Which report types count comes from ``INCENTIVE_REPORT_TYPES``; a nutrition survey
    is rewarded at most ``INCENTIVE_NUTRITION_PER_MONTH`` times per household per month.
    """
    settings = get_settings()
    if from_nutrition_survey and "nutrition" in settings.incentive_types:
        cap = max(0, settings.incentive_nutrition_per_month)
        if cap and nutrition_rewards_this_month(db, user) >= cap:
            return None
    every = max(1, settings.incentive_every_n_reports)
    count = incentivised_report_count(db, user)
    if count == 0 or count % every:
        return None
    result = send_airtime(user.phone_number, settings.incentive_amount_rwf)
    reason = (f"{count} reports incl. nutrition survey" if from_nutrition_survey
              else f"{count} weather/infrastructure reports")
    reward = IncentiveReward(field_user_id=user.id, phone_number=user.phone_number, amount_rwf=settings.incentive_amount_rwf,
                             reason=reason, status=result["status"], provider_id=result.get("provider_id"))
    db.add(reward)
    return reward
