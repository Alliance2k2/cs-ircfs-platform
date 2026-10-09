"""Cooperatives: CRUD, participation ranking and training progress (WP5).

Reads are open to district staff; CRUD is for district planners and administrators,
matching the concept's Section 8 (the pilot is planned and reviewed by the district).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells, cell_filter
from app.core.security import Principal, require_roles
from app.db.models import (
    Cell,
    Cooperative,
    FieldUser,
    IrrigationScheme,
    Sector,
    UserRole,
)
from app.db.session import get_db
from app.schemas import (
    CooperativeCreate,
    CooperativeParticipation,
    CooperativeRead,
    CooperativeUpdate,
    TrainingProgress,
)
from app.services import cooperatives as coop_service
from app.services.references import require_if_provided

router = APIRouter(prefix="/api/v1/cooperatives", tags=["cooperatives"])

READ_ROLES = (UserRole.district_officer, UserRole.district_planner, UserRole.administrator)
WRITE_ROLES = (UserRole.district_planner, UserRole.administrator)


def _sector_scope(principal: Principal) -> frozenset[int] | None:
    """None means the whole district; otherwise the cooperative's own sector."""
    return principal.sector_ids


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Cooperative not found")


def _get(db: Session, cooperative_id: int, principal: Principal) -> Cooperative:
    cooperative = db.get(Cooperative, cooperative_id)
    if not cooperative:
        raise _not_found()
    sectors = _sector_scope(principal)
    if sectors is not None and cooperative.sector_id not in sectors:
        raise _not_found()
    return cooperative


@router.get("", response_model=list[CooperativeRead])
def list_cooperatives(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*READ_ROLES)),
) -> list[Cooperative]:
    query = select(Cooperative).order_by(Cooperative.name)
    if principal.sector_ids is not None:
        query = query.where(Cooperative.sector_id.in_(principal.sector_ids))
    return list(db.scalars(query))


@router.get("/participation", response_model=list[CooperativeParticipation])
def cooperative_participation(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*READ_ROLES)),
) -> list[dict]:
    """Ranking for the Inteko z'Abaturage meeting: last 30 days and month to date."""
    return coop_service.ranking(db, cells=allowed_cells(db, principal), sector_ids=_sector_scope(principal))


@router.get("/training-progress", response_model=TrainingProgress)
def training_progress(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*READ_ROLES)),
) -> dict:
    """Trained Citizen Science Monitors against MONITOR_TRAINING_TARGET."""
    return coop_service.training_progress(db, cells=allowed_cells(db, principal))


@router.post("", response_model=CooperativeRead, status_code=status.HTTP_201_CREATED)
def create_cooperative(
    payload: CooperativeCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(*WRITE_ROLES)),
) -> Cooperative:
    existing = db.scalar(select(Cooperative).where(func.lower(Cooperative.name) == payload.name.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="A cooperative with this name already exists")
    require_if_provided(db, Sector, payload.sector_id, "sector_id")
    require_if_provided(db, IrrigationScheme, payload.irrigation_scheme_id, "irrigation_scheme_id")
    require_if_provided(db, FieldUser, payload.contact_field_user_id, "contact_field_user_id")
    cooperative = Cooperative(**payload.model_dump())
    db.add(cooperative)
    db.commit()
    db.refresh(cooperative)
    return cooperative


@router.patch("/{cooperative_id}", response_model=CooperativeRead)
def update_cooperative(
    cooperative_id: int,
    payload: CooperativeUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*WRITE_ROLES)),
) -> Cooperative:
    cooperative = _get(db, cooperative_id, principal)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("name"):
        clash = db.scalar(select(Cooperative).where(func.lower(Cooperative.name) == changes["name"].lower(), Cooperative.id != cooperative_id))
        if clash:
            raise HTTPException(status_code=409, detail="A cooperative with this name already exists")
    if "sector_id" in changes:
        require_if_provided(db, Sector, changes["sector_id"], "sector_id")
    if "irrigation_scheme_id" in changes:
        require_if_provided(db, IrrigationScheme, changes["irrigation_scheme_id"], "irrigation_scheme_id")
    if "contact_field_user_id" in changes:
        require_if_provided(db, FieldUser, changes["contact_field_user_id"], "contact_field_user_id")
    for field, value in changes.items():
        setattr(cooperative, field, value)
    db.commit()
    db.refresh(cooperative)
    return cooperative


@router.delete("/{cooperative_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cooperative(
    cooperative_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*WRITE_ROLES)),
) -> None:
    cooperative = _get(db, cooperative_id, principal)
    members = db.scalar(select(func.count()).select_from(FieldUser).where(FieldUser.cooperative_id == cooperative_id)) or 0
    if members:
        raise HTTPException(
            status_code=409,
            detail=f"{members} field user(s) still belong to this cooperative. Move them first.",
        )
    db.delete(cooperative)
    db.commit()
