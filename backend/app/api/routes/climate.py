"""Climate observations and administrator-approved historical reference documents."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.models import IrrigationScheme, RainfallReference, Sector, UserRole
from app.db.session import get_db
from app.schemas.climate_maintenance import RainfallReferenceCreate, ReferenceApproval
from app.services.audit import record
from app.services.climate import KIGALI, rainfall_analysis
from app.services.scheme_coverage import covering_sectors

router = APIRouter(prefix="/api/v1/climate", tags=["climate analytics"])
viewer = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
admin = Depends(require_roles(UserRole.administrator))


def reference_row(ref):
    return {name: getattr(ref, name) for name in ("id", "sector_id", "scheme_id", "period_start", "period_end",
        "reference_start_year", "reference_end_year", "mean_rainfall_mm", "source", "document_reference", "data_origin", "approved_at")}


@router.get("/rainfall")
def rainfall(start: date | None = None, end: date | None = None,
             sector_id: int | None = Query(default=None, gt=0), scheme_id: int | None = Query(default=None, gt=0),
             reference_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db), principal: Principal = viewer):
    end = end or datetime.now(KIGALI).date()
    start = start or end - timedelta(days=29)
    return rainfall_analysis(db, principal, start, end, sector_id, scheme_id, reference_id)


@router.get("/references")
def references(db: Session = Depends(get_db), principal: Principal = viewer):
    query = select(RainfallReference).order_by(RainfallReference.id.desc())
    if principal.sector_ids is not None:
        scheme_ids = select(IrrigationScheme.id).where(covering_sectors(principal.sector_ids))
        query = query.where((RainfallReference.sector_id.in_(principal.sector_ids)) | RainfallReference.scheme_id.in_(scheme_ids))
    return [reference_row(ref) for ref in db.scalars(query)]


@router.post("/references", status_code=201)
def create_reference(payload: RainfallReferenceCreate, db: Session = Depends(get_db), principal: Principal = admin):
    model, location_id = (Sector, payload.sector_id) if payload.sector_id else (IrrigationScheme, payload.scheme_id)
    if db.get(model, location_id) is None:
        raise HTTPException(422, "Unknown reference location")
    ref = RainfallReference(**payload.model_dump())
    db.add(ref)
    db.flush()
    record(db, principal, "rainfall_reference.create", "rainfall_reference", ref.id, **payload.model_dump())
    db.commit()
    db.refresh(ref)
    return reference_row(ref)


@router.post("/references/{reference_id}/approve")
def approve_reference(reference_id: int, payload: ReferenceApproval, db: Session = Depends(get_db), principal: Principal = admin):
    ref = db.scalar(select(RainfallReference).where(RainfallReference.id == reference_id).with_for_update())
    if ref is None:
        raise HTTPException(404, "Reference not found")
    if ref.approved_at:
        raise HTTPException(409, "Approved reference documents are immutable")
    if ref.data_origin == "demo" or ref.source.upper().startswith("DEMONSTRATION"):
        raise HTTPException(422, "Demonstration references cannot be approved")
    ref.approved_at = payload.approved_at
    ref.approved_by_account_id = principal.account_id
    record(db, principal, "rainfall_reference.approve", "rainfall_reference", ref.id, approved_at=payload.approved_at)
    db.commit()
    db.refresh(ref)
    return reference_row(ref)
