"""Incident case workflow for the Act Now queue."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells, check_cell
from app.core.security import Principal, require_roles
from app.db.models import IncidentCase, IncidentEvent, PlatformAccount, ReportStatus, UserRole
from app.db.session import get_db
from app.schemas import CellNotification, IncidentCaseRead, IncidentEventRead, IncidentUpdate
from app.services.audit import record
from app.services.cases import case_source, change_status, require_case_source, source_cell
from app.services.notifications import notify_cell, resolution_message
from app.services.references import require_if_provided

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])
planner = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.get("", response_model=list[IncidentCaseRead])
def list_cases(db: Session = Depends(get_db), principal: Principal = planner):
    cases = list(db.scalars(select(IncidentCase).order_by(IncidentCase.id.desc())))
    cells = allowed_cells(db, principal)
    return cases if cells is None else [case for case in cases if source_cell(db, case) in cells]


def find_case(db: Session, case_id: int, principal: Principal) -> IncidentCase:
    """The case, if it exists and lies in the person's area; otherwise 404."""
    case = db.get(IncidentCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    check_cell(source_cell(db, case), allowed_cells(db, principal), "Case")
    return case


@router.get("/{case_id}", response_model=IncidentCaseRead)
def get_case(case_id: int, db: Session = Depends(get_db), principal: Principal = planner):
    return find_case(db, case_id, principal)


@router.patch("/{case_id}", response_model=IncidentCaseRead)
def update_case(case_id: int, payload: IncidentUpdate, db: Session = Depends(get_db), principal: Principal = planner):
    case = find_case(db, case_id, principal)
    require_if_provided(db, PlatformAccount, payload.assigned_to_account_id, "assigned_to_account_id")
    if payload.status == ReportStatus.assigned and payload.assigned_to_account_id is None and case.assigned_to_account_id is None:
        raise HTTPException(status_code=422, detail="An assigned case needs an owner")
    change_status(db, case, payload.status, payload.action_taken, principal.account_id)
    if payload.assigned_to_account_id is not None:
        case.assigned_to_account_id = payload.assigned_to_account_id
    if payload.due_at is not None:
        case.due_at = payload.due_at
    record(db, principal, "case.update", "incident_case", case.id, status=payload.status.value,
           assigned_to_account_id=payload.assigned_to_account_id, due_at=payload.due_at)
    db.commit()
    db.refresh(case)
    return case


@router.get("/{case_id}/history", response_model=list[IncidentEventRead])
def case_history(case_id: int, db: Session = Depends(get_db), principal: Principal = planner):
    find_case(db, case_id, principal)
    return list(db.scalars(select(IncidentEvent).where(IncidentEvent.case_id == case_id).order_by(IncidentEvent.id.desc())))


@router.post("/{case_id}/simulate-notification", response_model=IncidentCaseRead)
def simulate_notification(case_id: int, db: Session = Depends(get_db), principal: Principal = planner):
    """Record a demonstration response; no SMS is sent."""
    case = find_case(db, case_id, principal)
    if case.status not in {ReportStatus.resolved, ReportStatus.closed}:
        raise HTTPException(status_code=422, detail="Resolve the case before notifying the reporter")
    case.reporter_notified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/notify-cell")
def notify_case_cell(case_id: int, payload: CellNotification, db: Session = Depends(get_db), principal: Principal = planner) -> dict:
    """Closing-the-Loop SMS for a resolved crop or infrastructure case."""
    case = find_case(db, case_id, principal)
    if case.status not in {ReportStatus.resolved, ReportStatus.closed}:
        raise HTTPException(status_code=422, detail="Resolve the case before notifying the community")
    # Fails with 409 if the source report has been deleted, instead of silently sending nothing.
    report = require_case_source(db, case)
    subject = report.infrastructure_name if case.source_type == "infrastructure" else (report.pest_or_disease or report.crop_type)
    message = payload.message or resolution_message(f"Ikibazo #{case.id}", subject or "raporo", case.action_taken)
    result = notify_cell(db, report.cell_id, message, payload.preview)
    if not payload.preview:
        case.reporter_notified_at = datetime.now(timezone.utc)
        record(db, principal, "case.notify_cell", "incident_case", case.id, recipients=result.get("recipients"))
    db.commit()
    return result
