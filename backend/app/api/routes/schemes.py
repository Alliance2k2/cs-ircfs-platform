"""Irrigation scheme endpoints: create, list, and record verified outcome targets."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import IrrigationScheme, Sector, UserRole
from app.db.session import get_db
from app.schemas import IrrigationSchemeCreate, IrrigationSchemeRead, IrrigationSchemeUpdate
from app.services.references import require_if_provided

router = APIRouter(prefix="/api/v1/irrigation-schemes", tags=["irrigation schemes"])
reader = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
admin = Depends(require_roles(UserRole.administrator))


@router.post("", response_model=IrrigationSchemeRead, status_code=status.HTTP_201_CREATED)
def create_irrigation_scheme(payload: IrrigationSchemeCreate, db: Session = Depends(get_db), _: object = admin) -> IrrigationScheme:
    if db.scalar(select(IrrigationScheme.id).where(IrrigationScheme.name == payload.name)) is not None:
        raise HTTPException(status_code=409, detail="An irrigation scheme with this name already exists")
    require_if_provided(db, Sector, payload.sector_id, "sector_id")
    scheme = IrrigationScheme(**payload.model_dump())
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return scheme


@router.get("", response_model=list[IrrigationSchemeRead])
def list_irrigation_schemes(db: Session = Depends(get_db), _: object = reader) -> list[IrrigationScheme]:
    return list(db.scalars(select(IrrigationScheme).order_by(IrrigationScheme.name)))


@router.patch("/{scheme_id}", response_model=IrrigationSchemeRead)
def update_irrigation_scheme(scheme_id: int, payload: IrrigationSchemeUpdate, db: Session = Depends(get_db), _: object = admin) -> IrrigationScheme:
    """Record verified scheme figures, e.g. the feasibility-study yield target used for outcome verification."""
    scheme = db.get(IrrigationScheme, scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Irrigation scheme not found")
    changes = payload.model_dump(exclude_unset=True)
    if "sector_id" in changes:
        require_if_provided(db, Sector, changes["sector_id"], "sector_id")
    if changes.get("baseline_yield_target_tons") is not None and not (changes.get("baseline_source") or scheme.baseline_source):
        raise HTTPException(status_code=422, detail="Give the source of the yield target (e.g. feasibility study and year)")
    for field, value in changes.items():
        setattr(scheme, field, value)
    db.commit()
    db.refresh(scheme)
    return scheme
