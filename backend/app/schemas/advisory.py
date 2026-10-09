"""Outbound advisory and closing-the-loop messaging schemas."""
from pydantic import BaseModel, Field


class AdvisorySmsCreate(BaseModel):
    phone_number: str = Field(min_length=9, max_length=20)
    message: str = Field(min_length=2, max_length=480)


class ScheduleBroadcast(BaseModel):
    sector_ids: list[int] | None = None
    preview: bool = False


class CellNotification(BaseModel):
    """Closing-the-loop SMS. Leave message empty to use the default Kinyarwanda text."""

    message: str | None = Field(default=None, max_length=480)
    preview: bool = False
