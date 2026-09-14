from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import Cell, CitizenScienceLog, CommunityFeedback, Farm, FeedbackStatusEvent, IncidentCase, IncidentEvent, IrrigationClimateLog, User, UserRole
from app.db.session import get_db
from app.schemas import UserCreate, UserRead, UserUpdate
from app.services.references import require_if_provided

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.administrator)),
) -> User:
    existing = db.scalar(select(User).where(User.phone_number == payload.phone_number))
    if existing:
        raise HTTPException(status_code=409, detail="A user with this phone number already exists")
    require_if_provided(db, Cell, payload.cell_id, "cell_id")
    values = payload.model_dump(exclude={"latitude", "longitude"})
    user = User(**values)
    if payload.latitude is not None and payload.longitude is not None:
        user.location = ST_SetSRID(ST_MakePoint(payload.longitude, payload.latitude), 4326) if db.bind.dialect.name == "postgresql" else f"POINT({payload.longitude} {payload.latitude})"
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserRead])
def list_users(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    role: UserRole | None = None,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator)),
) -> list[User]:
    query = select(User).order_by(User.id.desc())
    if q:
        term = f"%{q.strip()}%"
        query = query.where(User.full_name.ilike(term) | User.phone_number.ilike(term) | User.cooperative_name.ilike(term))
    if role:
        query = query.where(User.role == role)
    return list(db.scalars(query))


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.administrator)),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    changes = payload.model_dump(exclude_unset=True)
    latitude = changes.pop("latitude", None)
    longitude = changes.pop("longitude", None)
    if "cell_id" in changes:
        require_if_provided(db, Cell, changes["cell_id"], "cell_id")
    for field, value in changes.items():
        setattr(user, field, value)
    if latitude is not None and longitude is not None:
        user.location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) if db.bind.dialect.name == "postgresql" else f"POINT({longitude} {latitude})"
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.administrator)),
) -> None:
    """Permanently remove a user only when no historical record references them."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    references = (
        select(Farm.id).where(Farm.farmer_id == user_id),
        select(CitizenScienceLog.id).where(CitizenScienceLog.reporter_id == user_id),
        select(IrrigationClimateLog.id).where(IrrigationClimateLog.reporter_id == user_id),
        select(CommunityFeedback.id).where(or_(CommunityFeedback.reporter_id == user_id, CommunityFeedback.assigned_to_user_id == user_id)),
        select(FeedbackStatusEvent.id).where(FeedbackStatusEvent.changed_by_user_id == user_id),
        select(IncidentCase.id).where(IncidentCase.assigned_to_user_id == user_id),
        select(IncidentEvent.id).where(IncidentEvent.changed_by_user_id == user_id),
    )
    if any(db.scalar(query.limit(1)) is not None for query in references):
        raise HTTPException(status_code=409, detail="This user is linked to reports or case history. Deactivate the account instead.")
    try:
        db.delete(user)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This user is linked to other records. Deactivate the account instead.") from error
