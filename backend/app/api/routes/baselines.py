"""Append-only baseline versions with explicit administrator approval."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.models import IrrigationScheme, SchemeBaseline, UserRole
from app.db.session import get_db
from app.schemas.baselines import BaselineApproval, BaselineCreate, BaselineRead
from app.services.audit import record
from app.services.yield_evaluation import approved_baselines

router = APIRouter(prefix="/api/v1/scheme-baselines", tags=["official baselines"])
admin = Depends(require_roles(UserRole.administrator))
reader = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.district_officer,
                              UserRole.district_planner, UserRole.administrator))


def cohort(b):
    return b.crop_type.casefold(), b.season.casefold(), b.reference_year


@router.get("", response_model=list[BaselineRead])
def list_baselines(scheme_id: int | None = Query(default=None, gt=0),
                   db: Session = Depends(get_db), _: Principal = reader):
    query = select(SchemeBaseline).order_by(SchemeBaseline.id.desc())
    if scheme_id is not None:
        query = query.where(SchemeBaseline.scheme_id == scheme_id)
    return list(db.scalars(query))


@router.post("", response_model=BaselineRead, status_code=201)
def create_baseline(payload: BaselineCreate, db: Session = Depends(get_db), principal: Principal = admin):
    if db.get(IrrigationScheme, payload.scheme_id) is None:
        raise HTTPException(422, "Unknown irrigation scheme")
    if payload.supersedes_id:
        original = db.get(SchemeBaseline, payload.supersedes_id)
        if original is None or original.scheme_id != payload.scheme_id or cohort(original) != cohort(payload):
            raise HTTPException(422, "Replacement must reference the same scheme, crop, season and year")
    baseline = SchemeBaseline(**payload.model_dump())
    db.add(baseline)
    db.flush()
    record(db, principal, "baseline.create", "scheme_baseline", baseline.id, **payload.model_dump())
    db.commit()
    db.refresh(baseline)
    return baseline


@router.post("/{baseline_id}/approve", response_model=BaselineRead)
def approve_baseline(baseline_id: int, payload: BaselineApproval, db: Session = Depends(get_db), principal: Principal = admin):
    baseline = db.get(SchemeBaseline, baseline_id)
    if baseline is None:
        raise HTTPException(404, "Baseline not found")
    # Serialize approvals per scheme so concurrent versions cannot both become current.
    db.scalar(select(IrrigationScheme).where(IrrigationScheme.id == baseline.scheme_id).with_for_update())
    db.refresh(baseline)
    if baseline.verification_status == "verified":
        raise HTTPException(409, "Approved versions are immutable; create a replacement")
    if baseline.data_origin == "demo" or any(s.upper().startswith("DEMONSTRATION") for s in (baseline.official_source, baseline.document_reference)):
        raise HTTPException(422, "Demonstration targets cannot be approved as official evidence")
    current = [b for b in approved_baselines(db, baseline.scheme_id) if cohort(b) == cohort(baseline)]
    if current and (len(current) != 1 or baseline.supersedes_id != current[0].id):
        raise HTTPException(409, "An approved target exists; explicitly supersede its version")
    if baseline.supersedes_id and (not current or baseline.supersedes_id != current[0].id):
        raise HTTPException(409, "Only the current approved target may be superseded")
    baseline.verification_status = "verified"
    baseline.approved_at = payload.approved_at
    baseline.approved_by_account_id = principal.account_id
    record(db, principal, "baseline.approve", "scheme_baseline", baseline.id, approved_at=payload.approved_at)
    db.commit()
    db.refresh(baseline)
    return baseline
