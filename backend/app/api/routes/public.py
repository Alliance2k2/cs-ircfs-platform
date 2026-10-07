from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Cell, CitizenScienceLog, InboundMessage, IrrigationClimateLog, IrrigationScheme, Sector, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/public", tags=["public"])


@router.get("/overview")
def public_overview(db: Session = Depends(get_db)) -> dict:
    """Live totals and recent activity for the public home page.

    No sign-in is needed, so this returns counts and sector names only: never names,
    phone numbers, message text or grievances.
    """
    count = lambda query: db.scalar(query) or 0  # noqa: E731
    since = datetime.now(timezone.utc) - timedelta(days=30)
    crop_sectors = select(Cell.sector_id).join(CitizenScienceLog, CitizenScienceLog.cell_id == Cell.id).where(CitizenScienceLog.created_at >= since)
    water_sectors = select(Cell.sector_id).join(IrrigationClimateLog, IrrigationClimateLog.cell_id == Cell.id).where(IrrigationClimateLog.created_at >= since)

    recent = []
    crop_rows = db.execute(select(CitizenScienceLog, Sector.name).outerjoin(Cell, CitizenScienceLog.cell_id == Cell.id)
                           .outerjoin(Sector, Cell.sector_id == Sector.id).order_by(CitizenScienceLog.id.desc()).limit(6))
    for log, sector in crop_rows:
        kind, label = ("pest", f"Pest alert: {log.pest_or_disease}") if log.pest_or_disease else ("harvest", f"{log.crop_type} harvest report")
        recent.append({"kind": kind, "label": label, "sector": sector, "created_at": log.created_at})
    water_rows = db.execute(select(IrrigationClimateLog, Sector.name).outerjoin(Cell, IrrigationClimateLog.cell_id == Cell.id)
                            .outerjoin(Sector, Cell.sector_id == Sector.id).order_by(IrrigationClimateLog.id.desc()).limit(6))
    for log, sector in water_rows:
        if log.rainfall_mm is not None:
            kind, label = "rain", f"Rain gauge: {log.rainfall_mm:g} mm"
        elif log.operational_status in ("faulty", "offline"):
            kind, label = "fault", f"Irrigation asset reported {log.operational_status}"
        else:
            kind, label = "water", "Irrigation asset check"
        recent.append({"kind": kind, "label": label, "sector": sector, "created_at": log.created_at})
    recent.sort(key=lambda item: item["created_at"].replace(tzinfo=None) if item["created_at"] else datetime.min, reverse=True)

    return {
        "reports": count(select(func.count()).select_from(CitizenScienceLog)) + count(select(func.count()).select_from(IrrigationClimateLog)),
        "field_messages": count(select(func.count()).select_from(InboundMessage)),
        "farmers": count(select(func.count()).select_from(User).where(User.role == UserRole.farmer)),
        "monitors": count(select(func.count()).select_from(User).where(User.role == UserRole.citizen_science_monitor)),
        "active_schemes": count(select(func.count()).select_from(IrrigationScheme).where(IrrigationScheme.is_active.is_(True))),
        "sectors_reporting": count(select(func.count()).select_from(crop_sectors.union(water_sectors).subquery())),
        "sectors_total": count(select(func.count()).select_from(Sector)),
        "recent": recent[:6],
        "updated_at": datetime.now(timezone.utc),
    }
