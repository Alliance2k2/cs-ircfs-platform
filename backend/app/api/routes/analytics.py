from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import CitizenScienceLog, CommunityFeedback, IncidentCase, IrrigationClimateLog, IrrigationScheme, ReportStatus, User, UserRole
from app.db.session import get_db
from app.schemas import ActNowItem, DashboardSummary

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
planner = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.get("/dashboard-summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db), _: object = planner) -> DashboardSummary:
    registered_farmers = db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.farmer)) or 0
    crop_reports = db.scalar(select(func.count()).select_from(CitizenScienceLog)) or 0
    irrigation_reports = db.scalar(select(func.count()).select_from(IrrigationClimateLog)) or 0
    active_schemes = db.scalar(select(func.count()).select_from(IrrigationScheme).where(IrrigationScheme.is_active.is_(True))) or 0
    open_complaints = db.scalar(select(func.count()).select_from(CommunityFeedback).where(CommunityFeedback.status.not_in([ReportStatus.resolved, ReportStatus.closed]))) or 0
    faulty_assets = db.scalar(select(func.count()).select_from(IrrigationClimateLog).where(IrrigationClimateLog.operational_status.in_(["faulty", "offline"]))) or 0
    return DashboardSummary(registered_farmers=registered_farmers, total_reports=crop_reports + irrigation_reports, active_schemes=active_schemes, open_complaints=open_complaints, faulty_or_offline_assets=faulty_assets)


@router.get("/act-now", response_model=list[ActNowItem])
def act_now_queue(db: Session = Depends(get_db), _: object = planner) -> list[ActNowItem]:
    items: list[ActNowItem] = []
    active = [ReportStatus.open, ReportStatus.triaged, ReportStatus.assigned, ReportStatus.in_progress]
    for case in db.scalars(select(IncidentCase).where(IncidentCase.status.in_(active))):
        if case.source_type == "irrigation":
            report = db.get(IrrigationClimateLog, case.source_id)
            if not report:
                continue
            title = f"{report.infrastructure_name or 'Irrigation asset'} is {report.operational_status}"
            details = report.fault_description or report.bottleneck_category
            item_type = "infrastructure"
        else:
            report = db.get(CitizenScienceLog, case.source_id)
            if not report:
                continue
            title = f"{report.pest_or_disease or 'Crop risk'} reported for {report.crop_type}"
            details = report.notes
            item_type = "pest_or_disease"
        items.append(ActNowItem(item_type=item_type, item_id=case.id, priority=case.priority, title=title, status=case.status.value, scheme_id=report.scheme_id, cell_id=report.cell_id, created_at=case.created_at, assigned_to_user_id=case.assigned_to_user_id, due_at=case.due_at, details=details))
    for feedback in db.scalars(select(CommunityFeedback).where(CommunityFeedback.status.in_(active))):
        items.append(ActNowItem(item_type="community_feedback", item_id=feedback.id, priority="medium", title=feedback.category, status=feedback.status.value, scheme_id=feedback.scheme_id, cell_id=feedback.cell_id, created_at=feedback.created_at, assigned_to_user_id=feedback.assigned_to_user_id, due_at=feedback.due_at, details=feedback.message))
    priority_order = {"critical": 0, "high": 1, "medium": 2}
    return sorted(items, key=lambda item: (priority_order[item.priority], item.created_at))


@router.get("/farmer-summary", response_model=DashboardSummary)
def farmer_summary(db: Session = Depends(get_db), _: object = planner) -> DashboardSummary:
    farmers = db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.farmer, User.is_active.is_(True))) or 0
    crop_reports = db.scalar(select(func.count()).select_from(CitizenScienceLog)) or 0
    irrigation_reports = db.scalar(select(func.count()).select_from(IrrigationClimateLog)) or 0
    return DashboardSummary(registered_farmers=farmers, total_reports=crop_reports + irrigation_reports, active_schemes=0, open_complaints=0, faulty_or_offline_assets=0)
