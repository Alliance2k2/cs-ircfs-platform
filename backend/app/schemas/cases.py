"""Incident-case schemas for the Act Now queue."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.db.models import ReportStatus


class IncidentCaseRead(BaseModel):
    id: int
    source_type: str
    source_id: int
    priority: str
    status: ReportStatus
    assigned_to_account_id: int | None
    due_at: datetime | None
    action_taken: str | None
    reporter_notified_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class IncidentUpdate(BaseModel):
    status: ReportStatus
    assigned_to_account_id: int | None = Field(default=None, gt=0)
    due_at: datetime | None = None
    action_taken: str | None = Field(default=None, max_length=3000)

    @field_validator("action_taken")
    @classmethod
    def action_for_resolution(cls, value: str | None, info) -> str | None:
        if info.data.get("status") in {ReportStatus.resolved, ReportStatus.closed} and not (value or "").strip():
            raise ValueError("an action is required to resolve or close a case")
        return value


class IncidentEventRead(BaseModel):
    id: int
    case_id: int
    previous_status: ReportStatus | None
    new_status: ReportStatus
    action_taken: str | None
    changed_by_account_id: int | None
    created_at: datetime
    model_config = {"from_attributes": True}
