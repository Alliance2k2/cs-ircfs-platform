"""Act Now case creation, source resolution, and status changes.

Incident cases point at one report through a polymorphic ``(source_type, source_id)``
pair. There is no database foreign key across that pair, so every read here goes through
:func:`case_source`, which returns ``None`` when the report has been removed. Callers that
must act on the report use :func:`require_case_source` so a dangling case fails loudly
instead of silently doing nothing.
"""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import (
    SOURCE_CROP,
    SOURCE_INFRASTRUCTURE,
    SOURCE_TYPES,
    CitizenScienceLog,
    IncidentCase,
    IncidentEvent,
    IrrigationClimateLog,
    ReportStatus,
)

SOURCE_MODELS = {SOURCE_CROP: CitizenScienceLog, SOURCE_INFRASTRUCTURE: IrrigationClimateLog}


def case_source(db: Session, case: IncidentCase):
    """The report behind a case, or None if it no longer exists."""
    model = SOURCE_MODELS.get(case.source_type)
    return db.get(model, case.source_id) if model else None


def source_cell(db: Session, case: IncidentCase) -> int | None:
    report = case_source(db, case)
    return report.cell_id if report else None


def require_case_source(db: Session, case: IncidentCase):
    """Return the source report or raise 409: the case points at a deleted record."""
    report = case_source(db, case)
    if report is None:
        raise HTTPException(
            status_code=409,
            detail=f"Case #{case.id} points at a {case.source_type} report that no longer exists",
        )
    return report


def auto_create_case(db: Session, source_type: str, report, priority: str, summary: str) -> IncidentCase:
    """Create an Act Now case and alert district staff by SMS when it is urgent enough."""
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"Unknown case source type: {source_type}")
    # Imported here because notifications reaches out to the SMS provider.
    from app.services.notifications import alert_staff

    case = IncidentCase(source_type=source_type, source_id=report.id, priority=priority)
    db.add(case)
    db.flush()
    alert_staff(db, case, summary, report.cell_id)
    return case


def change_status(
    db: Session,
    case: IncidentCase,
    new_status: ReportStatus,
    action_taken: str | None,
    changed_by_account_id: int | None,
) -> IncidentCase:
    """Append an immutable audit event and apply a status change to a case."""
    db.add(
        IncidentEvent(
            case_id=case.id,
            previous_status=case.status,
            new_status=new_status,
            action_taken=action_taken,
            changed_by_account_id=changed_by_account_id,
        )
    )
    case.status = new_status
    if action_taken is not None:
        case.action_taken = action_taken
    if new_status in {ReportStatus.resolved, ReportStatus.closed}:
        case.updated_at = datetime.now(timezone.utc)
    return case
