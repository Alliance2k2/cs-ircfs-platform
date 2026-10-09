"""Cooperative schemas (WP5): CRUD, participation ranking, training progress."""
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class CooperativeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    sector_id: int | None = Field(default=None, gt=0)
    irrigation_scheme_id: int | None = Field(default=None, gt=0)
    is_pilot: bool = False
    contact_field_user_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def tidy_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("name must be at least 2 characters")
        return value


class CooperativeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    sector_id: int | None = Field(default=None, gt=0)
    irrigation_scheme_id: int | None = Field(default=None, gt=0)
    is_pilot: bool | None = None
    contact_field_user_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def tidy_name(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value else value


class CooperativeRead(BaseModel):
    id: int
    name: str
    sector_id: int | None
    irrigation_scheme_id: int | None
    is_pilot: bool
    contact_field_user_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CooperativeParticipation(BaseModel):
    """One cooperative's participation, ranked for the Inteko z'Abaturage meeting."""

    id: int
    name: str
    sector_id: int | None
    is_pilot: bool
    members: int
    data_champions: int
    reports_30d: int
    reports_mtd: int
    crop_reports_30d: int
    irrigation_reports_30d: int
    nutrition_surveys_30d: int
    active_reporters_30d: int
    last_report_at: datetime | None


class TrainingProgress(BaseModel):
    trained_monitors: int
    target: int
    percent: float
    monitors_total: int
    data_champions: int
    pilot_cooperatives: int
    pilot_target: int
    trained_on: date | None = None  # most recent training date recorded
