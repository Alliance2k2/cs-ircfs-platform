"""Field-user schemas: the USSD/SMS callers, never web accounts."""
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.db.models import UserRole


class FieldUserCreate(BaseModel):
    phone_number: str = Field(min_length=8, max_length=20)
    full_name: str | None = Field(default=None, max_length=120)
    role: UserRole = UserRole.farmer
    cooperative_name: str | None = Field(default=None, max_length=120)
    cooperative_id: int | None = Field(default=None, gt=0)
    cell_id: int | None = Field(default=None, gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_data_champion: bool = False
    trained_at: date | None = None
    training_notes: str | None = Field(default=None, max_length=500)

    @field_validator("phone_number")
    @classmethod
    def normalise_phone(cls, value: str) -> str:
        return value.replace(" ", "").replace("-", "")


class FieldUserRead(BaseModel):
    id: int
    phone_number: str
    full_name: str | None
    role: UserRole
    cooperative_name: str | None
    cooperative_id: int | None
    cell_id: int | None
    is_active: bool
    is_data_champion: bool
    trained_at: date | None
    training_notes: str | None
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FieldUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    role: UserRole | None = None
    cooperative_name: str | None = Field(default=None, max_length=120)
    cooperative_id: int | None = Field(default=None, gt=0)
    cell_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None
    is_data_champion: bool | None = None
    trained_at: date | None = None
    training_notes: str | None = Field(default=None, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
