"""Scoped receipt comparisons. Activity is not a scientific impact estimate."""
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells, cell_filter
from app.core.security import Principal
from app.db.models import Cell, CitizenScienceLog, FieldUser, IrrigationClimateLog
from app.services.evidence import counted, demo_mode


def activity(db: Session, principal: Principal, start: date, end: date, *,
             sector_id: int | None = None, cell_id: int | None = None,
             scheme_id: int | None = None, cooperative_id: int | None = None) -> dict:
    # Dates are local Rwanda calendar dates; receipt timestamps are stored in UTC.
    kigali = timezone(timedelta(hours=2))
    beginning = datetime.combine(start, time.min, kigali).astimezone(timezone.utc)
    ending = datetime.combine(end + timedelta(days=1), time.min, kigali).astimezone(timezone.utc)
    previous = beginning - (ending - beginning)
    cells = allowed_cells(db, principal)
    if sector_id is not None:
        selection = set(db.scalars(select(Cell.id).where(Cell.sector_id == sector_id)))
        cells = selection if cells is None else cells & selection
    if cell_id is not None:
        cells = {cell_id} if cells is None else cells & {cell_id}

    def conditions(model):
        result = [counted(model), cell_filter(model.cell_id, cells)]
        if scheme_id is not None:
            result.append(model.scheme_id == scheme_id)
        if cooperative_id is not None:
            # Current membership, not a reconstructed historical affiliation.
            result.append(model.reporter_id.in_(select(FieldUser.id).where(FieldUser.cooperative_id == cooperative_id)))
        return result

    current_count = previous_count = verified = located = 0
    for model in (CitizenScienceLog, IrrigationClimateLog):
        base = conditions(model)
        current = [*base, model.created_at >= beginning, model.created_at < ending]
        def count(*where):
            return db.scalar(select(func.count()).select_from(model).where(*where)) or 0
        current_count += count(*current)
        previous_count += count(*base, model.created_at >= previous, model.created_at < beginning)
        verified += count(*current, model.verification_status == "verified")
        located += count(*current, model.latitude.is_not(None), model.longitude.is_not(None))
    return {
        "start": start, "end": end, "previous_start": previous.astimezone(kigali).date(),
        "previous_end": start - timedelta(days=1), "reports": current_count,
        "previous_reports": previous_count, "change": current_count - previous_count,
        "verified_reports": verified, "located_reports": located, "demo_mode": demo_mode(db),
        "source": "live_unverified", "basis": "receipt_date",
        "membership_basis": "current_cooperative_membership",
    }
