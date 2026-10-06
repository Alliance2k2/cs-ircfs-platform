"""Irrigation Scheduling Assistant, Local Insights tips, nutrition scoring, and airtime incentives."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Cell, IncentiveReward, IrrigationClimateLog, Sector, User
from app.services.sms import send_airtime


@dataclass
class IrrigationAdvice:
    level: str
    rainfall_mm: float | None
    readings: int
    message_rw: str
    message_en: str


def advice_for_rainfall(total_mm: float | None, readings: int) -> IrrigationAdvice:
    """Translate 7-day rainfall into irrigation advice using the configured thresholds."""
    settings = get_settings()
    if not readings:
        return IrrigationAdvice("no_data", None, 0,
                                "Nta makuru y'imvura aheruka. Abafite ibipimo by'imvura, nimutwoherereze ibipimo.",
                                "No recent rainfall readings. Rain-gauge holders, please send today's reading.")
    mm = round(total_mm or 0.0, 1)
    if mm < settings.dry_spell_threshold_mm:
        return IrrigationAdvice("irrigate_more", mm, readings,
                                f"Inama: imvura yabaye nke ({mm} mm mu minsi 7). Ongera kuhira ho 10% muri iki cyumweru.",
                                f"Rainfall was low ({mm} mm in 7 days). Increase irrigation cycles by 10% this week.")
    if mm > settings.wet_spell_threshold_mm:
        return IrrigationAdvice("reduce", mm, readings,
                                f"Inama: imvura ihagije ({mm} mm mu minsi 7). Gabanya kuhira kugira ngo muzigame amazi.",
                                f"Rainfall is sufficient ({mm} mm in 7 days). Reduce irrigation to conserve water.")
    return IrrigationAdvice("normal", mm, readings,
                            f"Inama: imvura isanzwe ({mm} mm mu minsi 7). Komeza gahunda isanzwe yo kuhira.",
                            f"Rainfall is normal ({mm} mm in 7 days). Keep the usual irrigation schedule.")


def rainfall_by_sector(db: Session, days: int = 7) -> dict[int, tuple[float, int]]:
    """Return {sector_id: (total_mm, readings)} for citizen rain-gauge readings in the window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(Cell.sector_id, IrrigationClimateLog.reporter_id, IrrigationClimateLog.cell_id, IrrigationClimateLog.rainfall_mm)
        .join(Cell, Cell.id == IrrigationClimateLog.cell_id)
        .where(IrrigationClimateLog.rainfall_mm.is_not(None), IrrigationClimateLog.created_at >= cutoff)
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


def sector_schedule(db: Session) -> list[dict]:
    rainfall = rainfall_by_sector(db)
    rows = []
    for sector in db.scalars(select(Sector).order_by(Sector.name)):
        total, readings = rainfall.get(sector.id, (None, 0))
        advice = advice_for_rainfall(total, readings)
        rows.append({"sector_id": sector.id, "sector": sector.name, "level": advice.level, "rainfall_mm_7d": advice.rainfall_mm,
                     "readings": advice.readings, "message_rw": advice.message_rw, "message_en": advice.message_en,
                     "latitude": sector.latitude, "longitude": sector.longitude})
    return rows


def local_tip(db: Session, user: User) -> str:
    """'Local Insights' reply (architecture Section 8.3): give value back after every report."""
    sector_id = db.scalar(select(Cell.sector_id).where(Cell.id == user.cell_id)) if user.cell_id else None
    rainfall = rainfall_by_sector(db)
    if sector_id is not None:
        total, readings = rainfall.get(sector_id, (None, 0))
    else:
        values = list(rainfall.values())
        total, readings = (sum(v[0] for v in values) / len(values), sum(v[1] for v in values)) if values else (None, 0)
    return advice_for_rainfall(total, readings).message_rw


def nutrition_risk_score(meals_per_day: int, ate_protein_or_vegetables: bool, food_sufficient: bool) -> int:
    """1 (low risk) to 5 (high risk): fewer meals, no protein/vegetables, and food shortage add risk."""
    score = 1 + {1: 2, 2: 1}.get(meals_per_day, 0)
    score += 0 if ate_protein_or_vegetables else 1
    score += 0 if food_sufficient else 1
    return min(score, 5)


def maybe_reward(db: Session, user: User) -> IncentiveReward | None:
    """Every Nth weather or infrastructure report earns an airtime micro-bonus (Section 8.1)."""
    settings = get_settings()
    every = max(1, settings.incentive_every_n_reports)
    count = db.scalar(select(func.count()).select_from(IrrigationClimateLog).where(IrrigationClimateLog.reporter_id == user.id)) or 0
    if count == 0 or count % every:
        return None
    result = send_airtime(user.phone_number, settings.incentive_amount_rwf)
    reward = IncentiveReward(user_id=user.id, phone_number=user.phone_number, amount_rwf=settings.incentive_amount_rwf,
                             reason=f"{count} weather/infrastructure reports", status=result["status"], provider_id=result.get("provider_id"))
    db.add(reward)
    return reward
