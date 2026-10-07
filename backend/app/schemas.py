from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.db.models import ReportStatus, UserRole


class HealthResponse(BaseModel):
    status: str
    service: str

class AccountRegister(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=200)
    first_name: str = Field(min_length=1, max_length=80)
    middle_name: str | None = Field(default=None, max_length=80)
    surname: str = Field(min_length=1, max_length=80)

class AccountLogin(BaseModel):
    email: str
    password: str


class AccountRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


class AccountUpdate(BaseModel):
    role: UserRole | None = None
    status: str | None = Field(default=None, pattern="^(active|pending|suspended)$")


class UserCreate(BaseModel):
    phone_number: str = Field(min_length=8, max_length=20)
    full_name: str | None = Field(default=None, max_length=120)
    role: UserRole = UserRole.farmer
    cooperative_name: str | None = Field(default=None, max_length=120)
    cell_id: int | None = Field(default=None, gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("phone_number")
    @classmethod
    def normalise_phone(cls, value: str) -> str:
        return value.replace(" ", "").replace("-", "")


class UserRead(BaseModel):
    id: int
    phone_number: str
    full_name: str | None
    role: UserRole
    cooperative_name: str | None
    cell_id: int | None
    is_active: bool
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    role: UserRole | None = None
    cooperative_name: str | None = Field(default=None, max_length=120)
    cell_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class SectorRead(BaseModel):
    id: int
    name: str
    latitude: float | None
    longitude: float | None

    model_config = {"from_attributes": True}


class CellRead(BaseModel):
    id: int
    name: str
    sector_id: int
    latitude: float | None
    longitude: float | None

    model_config = {"from_attributes": True}


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


class CropReportCreate(BaseModel):
    reporter_id: int | None = Field(default=None, gt=0)
    scheme_id: int | None = Field(default=None, gt=0)
    cell_id: int | None = Field(default=None, gt=0)
    crop_type: str = Field(min_length=1, max_length=80)
    planting_date: date | None = None
    expected_harvest_tons: float | None = Field(default=None, ge=0)
    reported_harvest_tons: float | None = Field(default=None, ge=0)
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
    rainfall_mm: float | None = Field(default=None, ge=0, le=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class IrrigationReportRead(IrrigationReportCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


class FeedbackCreate(BaseModel):
    reporter_id: int | None = Field(default=None, gt=0)
    scheme_id: int | None = Field(default=None, gt=0)
    cell_id: int | None = Field(default=None, gt=0)
    category: str = Field(min_length=2, max_length=80)
    message: str = Field(min_length=5, max_length=3000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class FeedbackUpdate(BaseModel):
    status: ReportStatus
    action_taken: str | None = Field(default=None, max_length=3000)
    assigned_to_user_id: int | None = Field(default=None, gt=0)
    due_at: datetime | None = None
    changed_by_user_id: int | None = Field(default=None, gt=0)

    @field_validator("action_taken")
    @classmethod
    def require_action_when_resolved(cls, value: str | None, info) -> str | None:
        if info.data.get("status") in {ReportStatus.resolved, ReportStatus.closed} and not value:
            raise ValueError("an action taken is required when resolving or closing feedback")
        return value


class FeedbackRead(FeedbackCreate):
    id: int
    status: ReportStatus
    assigned_to_user_id: int | None
    due_at: datetime | None
    action_taken: str | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


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
    assigned_to_user_id: int | None = None
    due_at: datetime | None = None
    details: str | None = None


class MapFeature(BaseModel):
    id: str
    feature_type: str
    name: str
    latitude: float
    longitude: float
    status: str | None = None
    scheme_id: int | None = None
    details: str | None = None


class MapData(BaseModel):
    center: tuple[float, float]
    zoom: int
    features: list[MapFeature]


class FeedbackEventRead(BaseModel):
    id: int
    feedback_id: int
    previous_status: ReportStatus | None
    new_status: ReportStatus
    action_taken: str | None
    changed_by_user_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentCaseRead(BaseModel):
    id: int
    source_type: str
    source_id: int
    priority: str
    status: ReportStatus
    assigned_to_user_id: int | None
    due_at: datetime | None
    action_taken: str | None
    reporter_notified_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class IncidentUpdate(BaseModel):
    status: ReportStatus
    assigned_to_user_id: int | None = Field(default=None, gt=0)
    due_at: datetime | None = None
    action_taken: str | None = Field(default=None, max_length=3000)
    changed_by_user_id: int | None = Field(default=None, gt=0)

    @field_validator("action_taken")
    @classmethod
    def action_for_resolution(cls, value: str | None, info) -> str | None:
        if info.data.get("status") in {ReportStatus.resolved, ReportStatus.closed} and not (value or "").strip():
            raise ValueError("an action is required to resolve or close a case")
        return value


class IncidentEventRead(BaseModel):
    id: int
    case_id: int
    previous_status: ReportStatus | None
    new_status: ReportStatus
    action_taken: str | None
    changed_by_user_id: int | None
    created_at: datetime
    model_config = {"from_attributes": True}


class IrrigationSchemeUpdate(BaseModel):
    implementing_partner: str | None = Field(default=None, max_length=100)
    hectares_developed: float | None = Field(default=None, ge=0)
    baseline_yield_target_tons: float | None = Field(default=None, ge=0)
    baseline_source: str | None = Field(default=None, max_length=255)
    sector_id: int | None = Field(default=None, gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool | None = None


class AdvisorySmsCreate(BaseModel):
    phone_number: str = Field(min_length=9, max_length=20)
    message: str = Field(min_length=2, max_length=480)


class CellNotification(BaseModel):
    """Closing-the-loop SMS. Leave message empty to use the default Kinyarwanda text."""
    message: str | None = Field(default=None, max_length=480)
    preview: bool = False


class ScheduleBroadcast(BaseModel):
    sector_ids: list[int] | None = None
    preview: bool = False


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

