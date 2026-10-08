"""Area-level access: which cells a signed-in person may see records from.

Administrators, service API keys, local development, and accounts with no linked
sectors see the whole district (None). Everyone else sees records whose cell lies in
one of their sectors. Records without a cell are visible district-wide only.
District totals, trends and maps of counts stay district-wide: they hold no personal data.
"""
from fastapi import HTTPException
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from app.core.security import Principal
from app.db.models import CitizenScienceLog, Cell, IncidentCase, IrrigationClimateLog


def allowed_cells(db: Session, principal: Principal) -> set[int] | None:
    if principal.sector_ids is None:
        return None
    return set(db.scalars(select(Cell.id).where(Cell.sector_id.in_(principal.sector_ids))))


def cell_filter(column, cells: set[int] | None):
    """A WHERE clause limiting a cell_id column to the person's area."""
    return true() if cells is None else column.in_(cells)


def check_cell(cell_id: int | None, cells: set[int] | None, what: str) -> None:
    """Out-of-area records answer 404, exactly as if they did not exist."""
    if cells is not None and cell_id not in cells:
        raise HTTPException(status_code=404, detail=f"{what} not found")


def case_cell(db: Session, case: IncidentCase) -> int | None:
    report = db.get(IrrigationClimateLog if case.source_type == "irrigation" else CitizenScienceLog, case.source_id)
    return report.cell_id if report else None
