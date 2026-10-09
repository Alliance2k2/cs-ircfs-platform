"""Community feedback schemas. Grievances are always anonymous: no reporter is accepted."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.db.models import ReportStatus


class FeedbackCreate(BaseModel):
    scheme_id: int | None = Field(default=None, gt=0)
    cell_id: int | None = Field(default=None, gt=0)
    category: str = Field(min_length=2, max_length=80)
    message: str = Field(min_length=5, max_length=3000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class FeedbackUpdate(BaseModel):
    status: ReportStatus
    action_taken: str | None = Field(default=None, max_length=3000)
    assigned_to_field_user_id: int | None = Field(default=None, gt=0)
    due_at: datetime | None = None

    @field_validator("action_taken")
    @classmethod
    def require_action_when_resolved(cls, value: str | None, info) -> str | None:
        if info.data.get("status") in {ReportStatus.resolved, ReportStatus.closed} and not value:
            raise ValueError("an action taken is required when resolving or closing feedback")
        return value


class FeedbackRead(FeedbackCreate):
    id: int
    status: ReportStatus
    assigned_to_field_user_id: int | None
    due_at: datetime | None
    action_taken: str | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class FeedbackEventRead(BaseModel):
    id: int
    feedback_id: int
    previous_status: ReportStatus | None
    new_status: ReportStatus
    action_taken: str | None
    changed_by_account_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
