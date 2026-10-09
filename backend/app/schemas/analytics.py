"""Dashboard summary and Act Now queue schemas."""
from datetime import datetime

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    registered_farmers: int
    total_reports: int
    active_schemes: int
    open_complaints: int
    faulty_or_offline_assets: int
    households_surveyed: int = 0
    average_stunting_risk: float | None = None
    rewards_paid_rwf: int = 0
    field_messages: int = 0


class ActNowItem(BaseModel):
    item_type: str
    item_id: int
    priority: str
    title: str
    status: str
    scheme_id: int | None
    cell_id: int | None
    created_at: datetime
    assigned_to_account_id: int | None = None
    assigned_to_field_user_id: int | None = None
    due_at: datetime | None = None
    details: str | None = None
