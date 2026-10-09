"""Field report endpoints: crop, irrigation, and household nutrition."""
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells, cell_filter
from app.core.security import Principal, require_roles
from app.db.models import CitizenScienceLog, IrrigationClimateLog, NutritionSurvey, UserRole
from app.db.session import get_db
from app.schemas import (
    CropReportCreate,
    CropReportRead,
    IrrigationReportCreate,
    IrrigationReportRead,
    NutritionSurveyCreate,
    NutritionSurveyRead,
)
from app.services import reporting
from app.services.advisory import nutrition_risk_score
from app.services.references import validate_report_references

router = APIRouter(prefix="/api/v1", tags=["reports"])
reporter = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.administrator))
reader = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.post("/citizen-reports", response_model=CropReportRead, status_code=status.HTTP_201_CREATED)
def create_crop_report(payload: CropReportCreate, db: Session = Depends(get_db), _: object = reporter) -> CitizenScienceLog:
    validate_report_references(db, payload.reporter_id, payload.scheme_id, payload.cell_id)
    report = reporting.create_crop_report(db, **payload.model_dump())
    db.commit()
    db.refresh(report)
    return report


@router.get("/citizen-reports", response_model=list[CropReportRead])
def list_crop_reports(db: Session = Depends(get_db), principal: Principal = reader) -> list[CitizenScienceLog]:
    cells = allowed_cells(db, principal)
    return list(db.scalars(select(CitizenScienceLog).where(cell_filter(CitizenScienceLog.cell_id, cells)).order_by(CitizenScienceLog.id.desc())))


@router.post("/irrigation-reports", response_model=IrrigationReportRead, status_code=status.HTTP_201_CREATED)
def create_irrigation_report(payload: IrrigationReportCreate, db: Session = Depends(get_db), _: object = reporter) -> IrrigationClimateLog:
    validate_report_references(db, payload.reporter_id, payload.scheme_id, payload.cell_id)
    report = reporting.create_irrigation_report(db, **payload.model_dump())
    db.commit()
    db.refresh(report)
    return report


@router.get("/irrigation-reports", response_model=list[IrrigationReportRead])
def list_irrigation_reports(db: Session = Depends(get_db), principal: Principal = reader) -> list[IrrigationClimateLog]:
    cells = allowed_cells(db, principal)
    return list(db.scalars(select(IrrigationClimateLog).where(cell_filter(IrrigationClimateLog.cell_id, cells)).order_by(IrrigationClimateLog.id.desc())))


@router.post("/nutrition-surveys", response_model=NutritionSurveyRead, status_code=status.HTTP_201_CREATED)
def create_nutrition_survey(payload: NutritionSurveyCreate, db: Session = Depends(get_db), _: object = reporter) -> NutritionSurvey:
    """Household Nutrition Tracker entry (also collected through USSD option 6)."""
    validate_report_references(db, payload.reporter_id, None, payload.cell_id)
    survey = NutritionSurvey(
        **payload.model_dump(),
        stunting_risk_score=nutrition_risk_score(payload.meals_per_day, payload.ate_protein_or_vegetables, payload.food_sufficient),
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


@router.get("/nutrition-surveys", response_model=list[NutritionSurveyRead])
def list_nutrition_surveys(db: Session = Depends(get_db), principal: Principal = reader) -> list[NutritionSurvey]:
    cells = allowed_cells(db, principal)
    return list(db.scalars(select(NutritionSurvey).where(cell_filter(NutritionSurvey.cell_id, cells)).order_by(NutritionSurvey.id.desc())))
