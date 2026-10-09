"""Analytics endpoints. Every handler is a thin delegator to :mod:`app.services.analytics`."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.models import UserRole
from app.db.session import get_db
from app.schemas import ActNowItem, DashboardSummary
from app.services import analytics as analytics_service
from app.services.reporting import build_monthly_report, build_trends

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
planner = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
# Citizen Science Monitors read the same live figures as planners; acting on cases stays with planners.
viewer = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.get("/dashboard-summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db), principal: Principal = viewer) -> DashboardSummary:
    return analytics_service.dashboard_summary(db, principal)


@router.get("/farmer-summary", response_model=DashboardSummary)
def farmer_summary(db: Session = Depends(get_db), _: Principal = planner) -> DashboardSummary:
    return analytics_service.farmer_summary(db)


@router.get("/monthly-report")
def monthly_report(month: str | None = None, db: Session = Depends(get_db), _: Principal = viewer) -> dict:
    """One month of field evidence for the district (month as YYYY-MM, Kigali time; default: this month)."""
    return build_monthly_report(db, month)


@router.get("/trends")
def trends(months: int = 12, db: Session = Depends(get_db), _: Principal = viewer) -> dict:
    """Month-by-month reports, rainfall, cases, harvests and nutrition for the trend charts."""
    return build_trends(db, months)


@router.get("/act-now", response_model=list[ActNowItem])
def act_now_queue(db: Session = Depends(get_db), principal: Principal = planner) -> list[ActNowItem]:
    return analytics_service.act_now_queue(db, principal)


@router.get("/scheme-performance")
def scheme_performance(db: Session = Depends(get_db), _: Principal = viewer) -> list[dict]:
    return analytics_service.scheme_performance(db)


@router.get("/response-health")
def response_health(db: Session = Depends(get_db), _: Principal = viewer) -> dict:
    return analytics_service.response_health(db)


@router.get("/pest-heatmap")
def pest_heatmap(days: int = 90, db: Session = Depends(get_db), _: Principal = viewer) -> list[dict]:
    return analytics_service.pest_heatmap(db, days)


@router.get("/rainfall-map")
def rainfall_map(days: int = 7, db: Session = Depends(get_db), _: Principal = viewer) -> list[dict]:
    return analytics_service.rainfall_map(db, days)


@router.get("/nutrition-summary")
def nutrition_summary(db: Session = Depends(get_db), _: Principal = viewer) -> dict:
    return analytics_service.nutrition_summary(db)
