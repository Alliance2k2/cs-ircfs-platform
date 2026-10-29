"""Field report schemas: crop, irrigation, and household nutrition."""
from datetime import date, datetime

from pydantic import BaseModel, Field, computed_field, field_validator


class CropReportCreate(BaseModel):
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
        if value and value > date.today():
            raise ValueError("planting date cannot be in the future")
        return value


class CropReportRead(CropReportCreate):
    id: int
    created_at: datetime

    @computed_field
    @property
    def yield_tons_per_hectare(self) -> float | None:
        if self.reported_harvest_tons is None or self.cultivated_area_hectares is None:
            return None
        if self.cultivated_area_hectares <= 0:
            return None
        return round(self.reported_harvest_tons / self.cultivated_area_hectares, 3)

    model_config = {"from_attributes": True}


class IrrigationReportCreate(BaseModel):
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


class IrrigationReportRead(IrrigationReportCreate):
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
