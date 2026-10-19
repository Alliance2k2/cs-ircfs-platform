"""Map data for the planner dashboard's switchable layers."""

from fastapi import APIRouter, Depends
from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.privacy import sees_personal_data
from app.core.scope import allowed_cells, cell_filter
from app.core.security import Principal, require_roles
from app.db.models import CitizenScienceLog, FieldUser, IrrigationClimateLog, IrrigationScheme, UserRole
from app.db.session import get_db
from app.schemas import MapData, MapFeature
from app.services.evidence import counted

router = APIRouter(prefix="/api/v1", tags=["map"])


def located(report) -> tuple[float, float] | None:
    """The report's own GPS point, or None. Positions are never generated: a report without
    coordinates is counted in ``unlocated`` instead of being drawn somewhere near its cell."""
    if report.latitude is not None and report.longitude is not None:
        return report.latitude, report.longitude
    return None


reader = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.get("/map-data", response_model=MapData)
def map_data(db: Session = Depends(get_db), principal: Principal = reader) -> MapData:
    """Points for the district map, within the person's area of work.

    Only recorded coordinates are drawn. Simulator tests are left out. Free-text notes and
    registered farmers (names and home locations) are personal data, for district staff only.
    """
    features: list[MapFeature] = []
    unlocated = 0
    area = allowed_cells(db, principal)
    personal = sees_personal_data(principal)
    postgis = db.bind.dialect.name == "postgresql"
    for scheme in db.scalars(select(IrrigationScheme).where(IrrigationScheme.is_active.is_(True)).order_by(IrrigationScheme.name)):
        if scheme.latitude is not None and scheme.longitude is not None:
            features.append(MapFeature(id=f"scheme-{scheme.id}", feature_type="scheme", name=scheme.name, latitude=scheme.latitude, longitude=scheme.longitude, scheme_id=scheme.id))
    for report in db.scalars(select(IrrigationClimateLog).where(cell_filter(IrrigationClimateLog.cell_id, area), counted(IrrigationClimateLog))
                             .order_by(IrrigationClimateLog.id.desc())):
        position = located(report)
        if position is None:
            unlocated += 1
            continue
        is_rain = report.operational_status is None and report.rainfall_mm is not None
        details = (report.fault_description or report.bottleneck_category) if personal else report.bottleneck_category
        features.append(MapFeature(id=f"irrigation-{report.id}", feature_type="rainfall" if is_rain else "irrigation",
                                   name=report.infrastructure_name or "Irrigation observation", latitude=position[0], longitude=position[1],
                                   status=f"{report.rainfall_mm:g} mm" if is_rain else report.operational_status, scheme_id=report.scheme_id, details=details))
    for report in db.scalars(select(CitizenScienceLog).where(cell_filter(CitizenScienceLog.cell_id, area), counted(CitizenScienceLog))
                             .order_by(CitizenScienceLog.id.desc())):
        position = located(report)
        if position is None:
            unlocated += 1
            continue
        features.append(MapFeature(id=f"crop-{report.id}", feature_type="crop", name=report.pest_or_disease or report.crop_type,
                                   latitude=position[0], longitude=position[1],
                                   status="pest alert" if report.severity and report.severity >= 4 else "reported",
                                   scheme_id=report.scheme_id, details=report.notes if personal else None))
    if personal:
        features += farmer_points(db, area, postgis)
    return MapData(center=(-2.28, 30.15), zoom=10, features=features, spatial_available=postgis, unlocated_reports=unlocated)


def farmer_points(db: Session, area, postgis: bool) -> list[MapFeature]:
    """Registered farmers who have a recorded location (district staff only)."""
    query = (
        select(FieldUser.id, FieldUser.full_name, ST_Y(FieldUser.location), ST_X(FieldUser.location))
        if postgis else select(FieldUser.id, FieldUser.full_name, FieldUser.location)
    ).where(FieldUser.role == UserRole.farmer, FieldUser.location.is_not(None), cell_filter(FieldUser.cell_id, area))
    points = []
    for row in db.execute(query):
        if postgis:
            farmer_id, name, latitude, longitude = row
        else:
            farmer_id, name, point = row
            try:
                longitude, latitude = map(float, point.removeprefix("POINT(").removesuffix(")").split())
            except (ValueError, AttributeError):
                continue
        points.append(MapFeature(id=f"farmer-{farmer_id}", feature_type="farmer", name=name or "Unnamed farmer",
                                 latitude=latitude, longitude=longitude, details="Registered farmer location"))
    return points
