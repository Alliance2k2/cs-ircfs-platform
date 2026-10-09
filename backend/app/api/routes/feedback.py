"""Community feedback: anonymous grievances and the closing-the-loop workflow."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells, cell_filter, check_cell
from app.core.security import Principal, require_roles
from app.db.models import CommunityFeedback, FeedbackStatusEvent, FieldUser, ReportStatus, UserRole
from app.db.session import get_db
from app.schemas import CellNotification, FeedbackCreate, FeedbackEventRead, FeedbackRead, FeedbackUpdate
from app.services.notifications import notify_cell, resolution_message
from app.services.references import require_if_provided, validate_report_references

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])
submitter = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.administrator))
manager = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.post("", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def create_feedback(payload: FeedbackCreate, db: Session = Depends(get_db), _: object = submitter) -> CommunityFeedback:
    validate_report_references(db, None, payload.scheme_id, payload.cell_id)
    # Grievances are always anonymous: the reporter is never accepted or stored.
    feedback = CommunityFeedback(**payload.model_dump(), reporter_id=None)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("", response_model=list[FeedbackRead])
def list_feedback(db: Session = Depends(get_db), principal: Principal = manager) -> list[CommunityFeedback]:
    cells = allowed_cells(db, principal)
    return list(db.scalars(select(CommunityFeedback).where(cell_filter(CommunityFeedback.cell_id, cells)).order_by(CommunityFeedback.id.desc())))


def find_feedback(db: Session, feedback_id: int, principal: Principal) -> CommunityFeedback:
    feedback = db.get(CommunityFeedback, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback case not found")
    check_cell(feedback.cell_id, allowed_cells(db, principal), "Feedback case")
    return feedback


@router.patch("/{feedback_id}", response_model=FeedbackRead)
def update_feedback(
    feedback_id: int,
    payload: FeedbackUpdate,
    db: Session = Depends(get_db),
    principal: Principal = manager,
) -> CommunityFeedback:
    feedback = find_feedback(db, feedback_id, principal)
    require_if_provided(db, FieldUser, payload.assigned_to_field_user_id, "assigned_to_field_user_id")
    event = FeedbackStatusEvent(
        feedback_id=feedback.id,
        previous_status=feedback.status,
        new_status=payload.status,
        action_taken=payload.action_taken,
        changed_by_account_id=principal.account_id,
    )
    feedback.status = payload.status
    feedback.action_taken = payload.action_taken
    feedback.assigned_to_field_user_id = payload.assigned_to_field_user_id
    feedback.due_at = payload.due_at
    db.add(event)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/{feedback_id}/history", response_model=list[FeedbackEventRead])
def feedback_history(feedback_id: int, db: Session = Depends(get_db), principal: Principal = manager) -> list[FeedbackStatusEvent]:
    find_feedback(db, feedback_id, principal)
    return list(
        db.scalars(
            select(FeedbackStatusEvent)
            .where(FeedbackStatusEvent.feedback_id == feedback_id)
            .order_by(FeedbackStatusEvent.created_at.desc())
        )
    )


@router.post("/{feedback_id}/notify-cell")
def notify_feedback_cell(feedback_id: int, payload: CellNotification, db: Session = Depends(get_db), principal: Principal = manager) -> dict:
    """Closing-the-Loop SMS: tell everyone registered in the affected cell what was done."""
    feedback = find_feedback(db, feedback_id, principal)
    if feedback.status not in {ReportStatus.resolved, ReportStatus.closed}:
        raise HTTPException(status_code=422, detail="Resolve the feedback case before notifying the community")
    message = payload.message or resolution_message(f"Ikibazo FB-{feedback.id:03d}", feedback.category, feedback.action_taken)
    result = notify_cell(db, feedback.cell_id, message, payload.preview)
    db.commit()
    return result
