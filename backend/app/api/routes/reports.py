from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import CitizenScienceLog, IncidentCase, IrrigationClimateLog, UserRole
from app.db.session import get_db
from app.schemas import CropReportCreate, CropReportRead, IrrigationReportCreate, IrrigationReportRead
from app.services.references import validate_report_references

router = APIRouter(prefix="/api/v1", tags=["reports"])
reporter = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.administrator))
reader = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.post("/citizen-reports", response_model=CropReportRead, status_code=status.HTTP_201_CREATED)
def create_crop_report(payload: CropReportCreate, db: Session = Depends(get_db), _: object = reporter) -> CitizenScienceLog:
    validate_report_references(db, payload.reporter_id, payload.scheme_id, payload.cell_id)
    report = CitizenScienceLog(**payload.model_dump())
    db.add(report)
    db.flush()
    if payload.severity is not None and payload.severity >= 4:
        db.add(IncidentCase(source_type="crop", source_id=report.id, priority="critical" if payload.severity == 5 else "high"))
    db.commit()
    db.refresh(report)
    return report


@router.get("/citizen-reports", response_model=list[CropReportRead])
def list_crop_reports(db: Session = Depends(get_db), _: object = reader) -> list[CitizenScienceLog]:
    return list(db.scalars(select(CitizenScienceLog).order_by(CitizenScienceLog.id.desc())))


@router.post("/irrigation-reports", response_model=IrrigationReportRead, status_code=status.HTTP_201_CREATED)
def create_irrigation_report(payload: IrrigationReportCreate, db: Session = Depends(get_db), _: object = reporter) -> IrrigationClimateLog:
    validate_report_references(db, payload.reporter_id, payload.scheme_id, payload.cell_id)
    report = IrrigationClimateLog(**payload.model_dump())
    db.add(report)
    db.flush()
    if payload.operational_status in {"faulty", "offline"}:
        db.add(IncidentCase(source_type="irrigation", source_id=report.id, priority="critical" if payload.operational_status == "offline" else "high"))
    db.commit()
    db.refresh(report)
    return report


@router.get("/irrigation-reports", response_model=list[IrrigationReportRead])
def list_irrigation_reports(db: Session = Depends(get_db), _: object = reader) -> list[IrrigationClimateLog]:
    return list(db.scalars(select(IrrigationClimateLog).order_by(IrrigationClimateLog.id.desc())))
