"""Field report endpoints: crop, irrigation, and household nutrition."""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells, cell_filter
from app.core.privacy import sees_personal_data
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
from app.services.audit import personal_read
from app.services.advisory import nutrition_risk_score
from app.services.references import validate_report_references, validate_report_scope

router = APIRouter(prefix="/api/v1", tags=["reports"])
reporter = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.administrator))
reader = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
# Household nutrition answers are personal data: district staff only. Monitors use the
# anonymised aggregate in /analytics/nutrition-summary.
household_reader = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.post("/citizen-reports", response_model=CropReportRead, status_code=status.HTTP_201_CREATED)
def create_crop_report(payload: CropReportCreate, db: Session = Depends(get_db), principal: Principal = reporter) -> CitizenScienceLog:
    validate_report_scope(db, principal, payload)
    validate_report_references(db, payload.reporter_id, payload.scheme_id, payload.cell_id)
    report = reporting.create_crop_report(db, **payload.model_dump())
    db.commit()
    db.refresh(report)
    return report


@router.get("/citizen-reports", response_model=list[CropReportRead])
def list_crop_reports(limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
                      db: Session = Depends(get_db), principal: Principal = reader) -> list[CitizenScienceLog]:
    cells = allowed_cells(db, principal)
    personal_read(db, principal, "citizensciencelog")
    rows = list(db.scalars(select(CitizenScienceLog).where(cell_filter(CitizenScienceLog.cell_id, cells))
                          .order_by(CitizenScienceLog.id.desc()).offset(offset).limit(limit)))

    result = [CropReportRead.model_validate(row).model_dump() for row in rows]
    if not sees_personal_data(principal):
        for row in result: row["notes"] = None
    return result


@router.post("/irrigation-reports", response_model=IrrigationReportRead, status_code=status.HTTP_201_CREATED)
def create_irrigation_report(payload: IrrigationReportCreate, db: Session = Depends(get_db), principal: Principal = reporter) -> IrrigationClimateLog:
    validate_report_scope(db, principal, payload)
    validate_report_references(db, payload.reporter_id, payload.scheme_id, payload.cell_id)
    report = reporting.create_irrigation_report(db, **payload.model_dump())
    db.commit()
    db.refresh(report)
    return report


@router.get("/irrigation-reports", response_model=list[IrrigationReportRead])
def list_irrigation_reports(limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
                            db: Session = Depends(get_db), principal: Principal = reader) -> list[IrrigationClimateLog]:
    cells = allowed_cells(db, principal)
    personal_read(db, principal, "irrigationclimatelog")
    rows = list(db.scalars(select(IrrigationClimateLog).where(cell_filter(IrrigationClimateLog.cell_id, cells))
                          .order_by(IrrigationClimateLog.id.desc()).offset(offset).limit(limit)))

    result = [IrrigationReportRead.model_validate(row).model_dump() for row in rows]
    if not sees_personal_data(principal):
        for row in result: row["fault_description"] = None
    return result


@router.post("/nutrition-surveys", response_model=NutritionSurveyRead, status_code=status.HTTP_201_CREATED)
def create_nutrition_survey(payload: NutritionSurveyCreate, db: Session = Depends(get_db), principal: Principal = reporter) -> NutritionSurvey:
    validate_report_scope(db, principal, payload)
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
def list_nutrition_surveys(limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
                           db: Session = Depends(get_db), principal: Principal = household_reader) -> list[NutritionSurvey]:
    cells = allowed_cells(db, principal)
    personal_read(db, principal, "nutrition_survey")
    return list(db.scalars(select(NutritionSurvey).where(cell_filter(NutritionSurvey.cell_id, cells))
                          .order_by(NutritionSurvey.id.desc()).offset(offset).limit(limit)))
