"""Calibration reference schemas (WP7): grievance categories and scheme assets."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class GrievanceCategoryCreate(BaseModel):
    code: str | None = Field(default=None, max_length=40)
    label_rw: str = Field(min_length=1, max_length=120)
    label_en: str = Field(min_length=1, max_length=80)
    sort_order: int = Field(default=0, ge=0, le=999)
    is_active: bool = True

    @field_validator("label_rw", "label_en")
    @classmethod
    def tidy(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("code")
    @classmethod
    def tidy_code(cls, value: str | None) -> str | None:
        return value.strip().lower().replace(" ", "_") if value else value


class GrievanceCategoryUpdate(BaseModel):
    label_rw: str | None = Field(default=None, min_length=1, max_length=120)
    label_en: str | None = Field(default=None, min_length=1, max_length=80)
    sort_order: int | None = Field(default=None, ge=0, le=999)
    is_active: bool | None = None

    @field_validator("label_rw", "label_en")
    @classmethod
    def tidy(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value else value


class GrievanceCategoryRead(BaseModel):
    id: int
    code: str
    label_rw: str
    label_en: str
    sort_order: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SchemeAssetCreate(BaseModel):
    name_rw: str = Field(min_length=1, max_length=120)
    name_en: str = Field(min_length=1, max_length=120)
    scheme_id: int | None = Field(default=None, gt=0)
    asset_type: str | None = Field(default=None, max_length=40)
    is_active: bool = True

    @field_validator("name_rw", "name_en")
    @classmethod
    def tidy(cls, value: str) -> str:
        return " ".join(value.split())


class SchemeAssetUpdate(BaseModel):
    name_rw: str | None = Field(default=None, min_length=1, max_length=120)
    name_en: str | None = Field(default=None, min_length=1, max_length=120)
    scheme_id: int | None = Field(default=None, gt=0)
    asset_type: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None

    @field_validator("name_rw", "name_en")
    @classmethod
    def tidy(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value else value


class SchemeAssetRead(BaseModel):
    id: int
    scheme_id: int | None
    name_rw: str
    name_en: str
    asset_type: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
