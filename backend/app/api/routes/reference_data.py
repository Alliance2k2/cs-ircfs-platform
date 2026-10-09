"""Reference geography: the sector and cell lists used by pickers and filters."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import Cell, Sector, UserRole
from app.db.session import get_db
from app.schemas import CellRead, SectorRead

router = APIRouter(prefix="/api/v1", tags=["reference data"])
reader = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.get("/sectors", response_model=list[SectorRead])
def list_sectors(db: Session = Depends(get_db), _: object = reader) -> list[Sector]:
    return list(db.scalars(select(Sector).order_by(Sector.name)))


@router.get("/cells", response_model=list[CellRead])
def list_cells(db: Session = Depends(get_db), _: object = reader) -> list[Cell]:
    return list(db.scalars(select(Cell).order_by(Cell.name)))
