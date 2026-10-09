"""Field users: the USSD/SMS callers. Never web accounts (see /api/v1/auth/accounts)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells, cell_filter
from app.core.security import Principal, require_roles
from app.db.models import (
    Cell,
    CitizenScienceLog,
    CommunityFeedback,
    Cooperative,
    FieldUser,
    IncentiveReward,
    IrrigationClimateLog,
    NutritionSurvey,
    UserRole,
)
from app.db.session import get_db
from app.schemas import FieldUserCreate, FieldUserRead, FieldUserUpdate
from app.services.references import require_if_provided

router = APIRouter(prefix="/api/v1/field-users", tags=["field users"])


@router.post("", response_model=FieldUserRead, status_code=status.HTTP_201_CREATED)
def create_field_user(
    payload: FieldUserCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.administrator)),
) -> FieldUser:
    existing = db.scalar(select(FieldUser).where(FieldUser.phone_number == payload.phone_number))
    if existing:
        raise HTTPException(status_code=409, detail="A field user with this phone number already exists")
    require_if_provided(db, Cell, payload.cell_id, "cell_id")
    require_if_provided(db, Cooperative, payload.cooperative_id, "cooperative_id")
    values = payload.model_dump(exclude={"latitude", "longitude"})
    user = FieldUser(**values)
    if payload.latitude is not None and payload.longitude is not None:
        user.location = (
            ST_SetSRID(ST_MakePoint(payload.longitude, payload.latitude), 4326)
            if db.bind.dialect.name == "postgresql"
            else f"POINT({payload.longitude} {payload.latitude})"
        )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[FieldUserRead])
def list_field_users(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    role: UserRole | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator)),
) -> list[FieldUser]:
    query = select(FieldUser).where(cell_filter(FieldUser.cell_id, allowed_cells(db, principal))).order_by(FieldUser.id.desc())
    if q:
        term = f"%{q.strip()}%"
        query = query.where(FieldUser.full_name.ilike(term) | FieldUser.phone_number.ilike(term) | FieldUser.cooperative_name.ilike(term))
    if role:
        query = query.where(FieldUser.role == role)
    return list(db.scalars(query))


@router.patch("/{field_user_id}", response_model=FieldUserRead)
def update_field_user(
    field_user_id: int,
    payload: FieldUserUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.administrator)),
) -> FieldUser:
    user = db.get(FieldUser, field_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Field user not found")
    changes = payload.model_dump(exclude_unset=True)
    latitude = changes.pop("latitude", None)
    longitude = changes.pop("longitude", None)
    if "cell_id" in changes:
        require_if_provided(db, Cell, changes["cell_id"], "cell_id")
    if "cooperative_id" in changes:
        require_if_provided(db, Cooperative, changes["cooperative_id"], "cooperative_id")
    for field, value in changes.items():
        setattr(user, field, value)
    if latitude is not None and longitude is not None:
        user.location = (
            ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
            if db.bind.dialect.name == "postgresql"
            else f"POINT({longitude} {latitude})"
        )
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{field_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field_user(
    field_user_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.administrator)),
) -> None:
    """Permanently remove a field user only when no historical record references them."""
    user = db.get(FieldUser, field_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Field user not found")
    references = (
        select(CitizenScienceLog.id).where(CitizenScienceLog.reporter_id == field_user_id),
        select(IrrigationClimateLog.id).where(IrrigationClimateLog.reporter_id == field_user_id),
        select(NutritionSurvey.id).where(NutritionSurvey.reporter_id == field_user_id),
        select(IncentiveReward.id).where(IncentiveReward.field_user_id == field_user_id),
        select(CommunityFeedback.id).where(
            or_(CommunityFeedback.reporter_id == field_user_id, CommunityFeedback.assigned_to_field_user_id == field_user_id)
        ),
    )
    if any(db.scalar(query.limit(1)) is not None for query in references):
        raise HTTPException(status_code=409, detail="This field user is linked to reports or case history. Deactivate them instead.")
    try:
        db.delete(user)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This field user is linked to other records. Deactivate them instead.") from error
