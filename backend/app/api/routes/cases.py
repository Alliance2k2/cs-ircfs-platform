from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import IncidentCase, IncidentEvent, ReportStatus, User, UserRole
from app.db.session import get_db
from app.schemas import IncidentCaseRead, IncidentEventRead, IncidentUpdate
from app.services.references import require_if_provided

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])
planner = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.get("", response_model=list[IncidentCaseRead])
def list_cases(db: Session = Depends(get_db), _: object = planner):
    return list(db.scalars(select(IncidentCase).order_by(IncidentCase.id.desc())))


@router.get("/{case_id}", response_model=IncidentCaseRead)
def get_case(case_id: int, db: Session = Depends(get_db), _: object = planner):
    case = db.get(IncidentCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.patch("/{case_id}", response_model=IncidentCaseRead)
def update_case(case_id: int, payload: IncidentUpdate, db: Session = Depends(get_db), _: object = planner):
    case = db.get(IncidentCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    require_if_provided(db, User, payload.assigned_to_user_id, "assigned_to_user_id")
    require_if_provided(db, User, payload.changed_by_user_id, "changed_by_user_id")
    if payload.status == ReportStatus.assigned and payload.assigned_to_user_id is None and case.assigned_to_user_id is None:
        raise HTTPException(status_code=422, detail="An assigned case needs an owner")
    db.add(IncidentEvent(case_id=case.id, previous_status=case.status, new_status=payload.status, action_taken=payload.action_taken, changed_by_user_id=payload.changed_by_user_id))
    case.status = payload.status
    if payload.assigned_to_user_id is not None:
        case.assigned_to_user_id = payload.assigned_to_user_id
    if payload.due_at is not None:
        case.due_at = payload.due_at
    if payload.action_taken is not None:
        case.action_taken = payload.action_taken
    db.commit()
    db.refresh(case)
    return case


@router.get("/{case_id}/history", response_model=list[IncidentEventRead])
def case_history(case_id: int, db: Session = Depends(get_db), _: object = planner):
    if not db.get(IncidentCase, case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return list(db.scalars(select(IncidentEvent).where(IncidentEvent.case_id == case_id).order_by(IncidentEvent.id.desc())))


@router.post("/{case_id}/simulate-notification", response_model=IncidentCaseRead)
def simulate_notification(case_id: int, db: Session = Depends(get_db), _: object = planner):
    """Record a demonstration response; no SMS is sent."""
    case = db.get(IncidentCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.status not in {ReportStatus.resolved, ReportStatus.closed}:
        raise HTTPException(status_code=422, detail="Resolve the case before notifying the reporter")
    case.reporter_notified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(case)
    return case
