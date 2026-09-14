from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import Cell, IrrigationScheme, Sector, UserRole
from app.db.session import get_db
from app.schemas import CellRead, IrrigationSchemeCreate, IrrigationSchemeRead, SectorRead
from app.services.references import require_if_provided

router = APIRouter(prefix="/api/v1", tags=["reference data"])
reader = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.post("/irrigation-schemes", response_model=IrrigationSchemeRead, status_code=status.HTTP_201_CREATED)
def create_irrigation_scheme(payload: IrrigationSchemeCreate, db: Session = Depends(get_db), _: object = Depends(require_roles(UserRole.administrator))) -> IrrigationScheme:
    if db.scalar(select(IrrigationScheme.id).where(IrrigationScheme.name == payload.name)) is not None:
        raise HTTPException(status_code=409, detail="An irrigation scheme with this name already exists")
    require_if_provided(db, Sector, payload.sector_id, "sector_id")
    scheme = IrrigationScheme(**payload.model_dump())
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return scheme


@router.get("/irrigation-schemes", response_model=list[IrrigationSchemeRead])
def list_irrigation_schemes(db: Session = Depends(get_db), _: object = reader) -> list[IrrigationScheme]:
    return list(db.scalars(select(IrrigationScheme).order_by(IrrigationScheme.name)))


@router.get("/locations/sectors", response_model=list[SectorRead])
def list_sectors(db: Session = Depends(get_db), _: object = reader) -> list[Sector]:
    return list(db.scalars(select(Sector).order_by(Sector.name)))


@router.get("/locations/cells", response_model=list[CellRead])
def list_cells(db: Session = Depends(get_db), _: object = reader) -> list[Cell]:
    return list(db.scalars(select(Cell).order_by(Cell.name)))
