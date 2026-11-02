"""Versioned official targets; creation never implies approval."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.reports import today


class BaselineCreate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    scheme_id: int = Field(gt=0)
    crop_type: str = Field(min_length=1, max_length=80)
    season: str = Field(min_length=1, max_length=20)
    reference_year: int = Field(ge=1900, le=2100)
    expected_yield: float = Field(gt=0)
    yield_unit: Literal["t/ha", "kg/ha"]
    official_source: str = Field(min_length=1, max_length=255)
    document_reference: str = Field(min_length=1, max_length=255)
    data_origin: Literal["field", "import", "demo"] = "import"
    supersedes_id: int | None = Field(default=None, gt=0)

    @field_validator("crop_type", "season", "official_source", "document_reference")
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value


class BaselineRead(BaselineCreate):
    model_config = ConfigDict(from_attributes=True, allow_inf_nan=False)
    id: int
    verification_status: str
    approved_at: date | None
    approved_by_account_id: int | None
    created_at: datetime


class BaselineApproval(BaseModel):
    approved_at: date

    @field_validator("approved_at")
    @classmethod
    def not_future(cls, value):
        if value > today():
            raise ValueError("approval date cannot be in the future")
        return value
