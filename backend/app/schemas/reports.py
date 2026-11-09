"""Field report schemas: crop, irrigation, and household nutrition."""
from datetime import date, datetime, timezone, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.services.yield_evaluation import tonnes


def today():
    return datetime.now(timezone(timedelta(hours=2))).date()


class CropReportCreate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    reporter_id: int | None = Field(default=None, gt=0)
    scheme_id: int | None = Field(default=None, gt=0)
    cell_id: int | None = Field(default=None, gt=0)
    crop_type: str = Field(min_length=1, max_length=80)
    crop_variety: str | None = Field(default=None, max_length=80)
    planting_date: date | None = None
    expected_harvest_month: date | None = None
    expected_harvest_tons: float | None = Field(default=None, ge=0)
    reported_harvest_tons: float | None = Field(default=None, ge=0)
    cultivated_area_hectares: float | None = Field(default=None, gt=0, le=100000)
    harvested_area_hectares: float | None = Field(default=None, gt=0, le=100000)
    observed_quantity: float | None = Field(default=None, ge=0)
    harvest_unit: Literal["t", "kg"] | None = None
    observation_type: Literal["farmer_estimate", "measured", "historical_reference"] | None = None
    data_source: str | None = Field(default=None, min_length=1, max_length=255)
    reference_year: int | None = Field(default=None, ge=1900, le=2100)
    reporting_date: date | None = None
    harvest_date: date | None = None
    season: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9 _/-]{1,19}$")
    pest_or_disease: str | None = Field(default=None, max_length=120)
    severity: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = Field(default=None, max_length=2000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("planting_date")
    @classmethod
    def planting_not_future(cls, value: date | None) -> date | None:
        if value and value > today():
            raise ValueError("planting date cannot be in the future")
        return value

    @field_validator("crop_type", "data_source", "season")
    @classmethod
    def nonblank(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("value cannot be blank")
        return value

    @model_validator(mode="after")
    def consistent_measurements(self):
        if self.harvested_area_hectares is not None and self.cultivated_area_hectares is not None:
            if self.harvested_area_hectares > self.cultivated_area_hectares:
                raise ValueError("harvested area cannot exceed cultivated area")
        if self.harvest_date and (self.harvest_date > today() or self.planting_date and self.harvest_date < self.planting_date):
            raise ValueError("harvest date must follow planting and cannot be in the future")
        if self.reporting_date and (self.reporting_date > today() or self.harvest_date and self.reporting_date < self.harvest_date):
            raise ValueError("reporting date must follow harvest and cannot be in the future")
        if (self.observed_quantity is None) != (self.harvest_unit is None):
            raise ValueError("observed quantity and harvest unit must be supplied together")
        if self.observed_quantity is not None:
            converted = tonnes(self.observed_quantity, self.harvest_unit)
            if self.reported_harvest_tons is not None and abs(converted - self.reported_harvest_tons) > 1e-9:
                raise ValueError("observed quantity conflicts with reported tonnes")
            self.reported_harvest_tons = converted
        return self


class CropReportRead(CropReportCreate):
    id: int
    created_at: datetime

    @computed_field
    @property
    def yield_tons_per_hectare(self) -> float | None:
        if self.reported_harvest_tons is None or self.harvested_area_hectares is None:
            return None
        if self.harvested_area_hectares <= 0:
            return None
        return round(self.reported_harvest_tons / self.harvested_area_hectares, 3)

    model_config = ConfigDict(from_attributes=True, allow_inf_nan=False)


class IrrigationReportCreate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    observation_date: date | None = None
    gauge_code: str | None = Field(default=None, min_length=1, max_length=80)
    data_source: str | None = Field(default=None, min_length=1, max_length=255)
    reporter_id: int | None = Field(default=None, gt=0)
    scheme_id: int | None = Field(default=None, gt=0)
    cell_id: int | None = Field(default=None, gt=0)
    infrastructure_name: str | None = Field(default=None, max_length=120)
    operational_status: str | None = Field(default=None, pattern="^(operational|faulty|offline)$")
    bottleneck_category: str | None = Field(
        default=None, pattern="^(technical|social|institutional|environmental)$"
    )
    fault_description: str | None = Field(default=None, max_length=2000)
    rainfall_mm: float | None = Field(default=None, ge=0, le=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("observation_date")
    @classmethod
    def observation_not_future(cls, value):
        if value and value > today():
            raise ValueError("observation date cannot be in the future")
        return value

    @field_validator("gauge_code", "data_source")
    @classmethod
    def nonblank_source(cls, value):
        if value is not None and not value.strip():
            raise ValueError("source and gauge code cannot be blank")
        return value.strip() if value is not None else None


class IrrigationReportRead(IrrigationReportCreate):
    # Older phone handlers accepted values above today's write limit. Preserve those
    # original observations for review; quality flags identify them as unusual.
    rainfall_mm: float | None = Field(default=None, allow_inf_nan=False)
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


class NutritionSurveyCreate(BaseModel):
    reporter_id: int | None = Field(default=None, gt=0)
    cell_id: int | None = Field(default=None, gt=0)
    meals_per_day: int = Field(ge=1, le=3)
    ate_protein_or_vegetables: bool
    food_sufficient: bool


class NutritionSurveyRead(NutritionSurveyCreate):
    id: int
    stunting_risk_score: int
    created_at: datetime
    model_config = {"from_attributes": True}
