"""Validated reference documents and explicit maintenance records."""
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.reports import today


class RecordInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @field_validator("*", mode="after")
    @classmethod
    def tidy(cls, value):
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("Text fields cannot be blank")
            return value.strip()
        return value


class RainfallReferenceCreate(RecordInput):
    sector_id: int | None = Field(default=None, gt=0)
    scheme_id: int | None = Field(default=None, gt=0)
    period_start: date
    period_end: date
    reference_start_year: int = Field(ge=1900, le=2100)
    reference_end_year: int = Field(ge=1900, le=2100)
    mean_rainfall_mm: float = Field(ge=0, le=100000)
    source: str = Field(min_length=1, max_length=255)
    document_reference: str = Field(min_length=1, max_length=255)
    data_origin: Literal["field", "import", "demo"] = "import"

    @model_validator(mode="after")
    def valid_period(self):
        if (self.sector_id is None) == (self.scheme_id is None):
            raise ValueError("Choose exactly one sector or irrigation scheme")
        if not 0 <= (self.period_end - self.period_start).days < 366:
            raise ValueError("Comparison window must contain 1 to 366 days")
        if self.reference_start_year > self.reference_end_year or self.reference_end_year >= self.period_start.year:
            raise ValueError("Historical reference years must precede the comparison period")
        return self


class ReferenceApproval(RecordInput):
    approved_at: date

    @field_validator("approved_at")
    @classmethod
    def not_future(cls, value):
        if value > today():
            raise ValueError("Approval date cannot be in the future")
        return value


class OutageCreate(RecordInput):
    asset_id: int = Field(gt=0)
    cell_id: int | None = Field(default=None, gt=0)
    started_at: AwareDatetime
    category: Literal["technical", "social", "institutional", "environmental"]
    description: str = Field(min_length=1, max_length=2000)
    source: str = Field(min_length=1, max_length=255)
    data_origin: Literal["field", "import", "demo"] = "field"

    @field_validator("started_at")
    @classmethod
    def start_not_future(cls, value):
        if value > datetime.now(timezone.utc):
            raise ValueError("Outage cannot start in the future")
        return value


class MaintenanceCreate(RecordInput):
    asset_id: int = Field(gt=0)
    cell_id: int | None = Field(default=None, gt=0)
    outage_id: int | None = Field(default=None, gt=0)
    performed_at: AwareDatetime
    kind: Literal["inspection", "preventive", "repair"]
    action: str = Field(min_length=1, max_length=2000)
    source: str = Field(min_length=1, max_length=255)
    restored: bool = False
    data_origin: Literal["field", "import", "demo"] = "field"

    @field_validator("performed_at")
    @classmethod
    def not_future(cls, value):
        if value > datetime.now(timezone.utc):
            raise ValueError("Maintenance cannot be recorded in the future")
        return value

    @model_validator(mode="after")
    def restoration_requires_repair(self):
        if self.restored and (self.outage_id is None or self.kind != "repair"):
            raise ValueError("Restoration requires a repair linked to an outage")
        return self
