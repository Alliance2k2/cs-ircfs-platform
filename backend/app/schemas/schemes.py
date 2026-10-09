"""Irrigation scheme schemas."""
from pydantic import BaseModel, Field, field_validator


class IrrigationSchemeRead(BaseModel):
    id: int
    name: str
    implementing_partner: str | None
    hectares_developed: float | None
    baseline_yield_target_tons: float | None
    baseline_source: str | None
    sector_id: int | None
    latitude: float | None
    longitude: float | None
    is_active: bool

    model_config = {"from_attributes": True}


class IrrigationSchemeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    implementing_partner: str | None = Field(default=None, max_length=100)
    hectares_developed: float | None = Field(default=None, ge=0)
    baseline_yield_target_tons: float | None = Field(default=None, ge=0)
    baseline_source: str | None = Field(default=None, max_length=255)
    sector_id: int | None = Field(default=None, gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("scheme name cannot be blank")
        return value


class IrrigationSchemeUpdate(BaseModel):
    implementing_partner: str | None = Field(default=None, max_length=100)
    hectares_developed: float | None = Field(default=None, ge=0)
    baseline_yield_target_tons: float | None = Field(default=None, ge=0)
    baseline_source: str | None = Field(default=None, max_length=255)
    sector_id: int | None = Field(default=None, gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool | None = None
