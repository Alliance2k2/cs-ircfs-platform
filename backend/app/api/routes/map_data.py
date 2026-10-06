import math

from fastapi import APIRouter, Depends
from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import Cell, CitizenScienceLog, IrrigationClimateLog, IrrigationScheme, User, UserRole
from app.db.session import get_db
from app.schemas import MapData, MapFeature

router = APIRouter(prefix="/api/v1", tags=["map"])


def located(report, cells: dict) -> tuple[float, float] | None:
    """Use the report's own point, else its cell centre with a small fixed offset so
    several reports from one cell stay individually clickable."""
    if report.latitude is not None and report.longitude is not None:
        return report.latitude, report.longitude
    cell = cells.get(report.cell_id)
    if not cell or cell.latitude is None or cell.longitude is None:
        return None
    angle = (report.id * 137.508) % 360
    radius = 0.002 + (report.id % 5) * 0.0012
    return cell.latitude + radius * math.sin(math.radians(angle)), cell.longitude + radius * math.cos(math.radians(angle))
reader = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.get("/map-data", response_model=MapData)
def map_data(db: Session = Depends(get_db), _: object = reader) -> MapData:
    features: list[MapFeature] = []
    schemes = list(db.scalars(select(IrrigationScheme).where(IrrigationScheme.is_active.is_(True)).order_by(IrrigationScheme.name)))
    cells = {cell.id: cell for cell in db.scalars(select(Cell))}

    for scheme in schemes:
        if scheme.latitude is not None and scheme.longitude is not None:
            features.append(MapFeature(id=f"scheme-{scheme.id}", feature_type="scheme", name=scheme.name, latitude=scheme.latitude, longitude=scheme.longitude, scheme_id=scheme.id))

    for report in db.scalars(select(IrrigationClimateLog).order_by(IrrigationClimateLog.id.desc())):
        position = located(report, cells)
        if position:
            is_rain = report.operational_status is None and report.rainfall_mm is not None
            features.append(MapFeature(id=f"irrigation-{report.id}", feature_type="rainfall" if is_rain else "irrigation", name=report.infrastructure_name or "Irrigation observation", latitude=position[0], longitude=position[1], status=f"{report.rainfall_mm:g} mm" if is_rain else report.operational_status, scheme_id=report.scheme_id, details=report.fault_description or report.bottleneck_category))

    for report in db.scalars(select(CitizenScienceLog).order_by(CitizenScienceLog.id.desc())):
        position = located(report, cells)
        if position:
            features.append(MapFeature(id=f"crop-{report.id}", feature_type="crop", name=report.pest_or_disease or report.crop_type, latitude=position[0], longitude=position[1], status="pest alert" if report.severity and report.severity >= 4 else "reported", scheme_id=report.scheme_id, details=report.notes))

    farmer_query = select(User.id, User.full_name, ST_Y(User.location), ST_X(User.location)).where(User.role == UserRole.farmer, User.location.is_not(None)) if db.bind.dialect.name == "postgresql" else select(User.id, User.full_name, User.location).where(User.role == UserRole.farmer, User.location.is_not(None))
    for row in db.execute(farmer_query):
        if db.bind.dialect.name == "postgresql":
            farmer_id, name, latitude, longitude = row
        else:
            farmer_id, name, point = row
            try:
                longitude, latitude = map(float, point.removeprefix("POINT(").removesuffix(")").split())
            except (ValueError, AttributeError):
                continue
        features.append(MapFeature(id=f"farmer-{farmer_id}", feature_type="farmer", name=name or "Unnamed farmer", latitude=latitude, longitude=longitude, details="Registered farmer location"))

    # District overview. Individual markers are only returned for records with coordinates.
    return MapData(center=(-2.28, 30.15), zoom=10, features=features)
