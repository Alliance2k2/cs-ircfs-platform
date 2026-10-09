"""GeoJSON boundaries and farmer points.

These overlays need PostGIS. Without it (local SQLite development) the endpoints return
empty lists and the dashboard shows a "Spatial features require PostgreSQL" notice.
"""
import json

from fastapi import APIRouter, Depends
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import Cell, FieldUser, Sector, UserRole
from app.db.session import get_db
from app.schemas import GeometryRead

router = APIRouter(prefix="/api/v1/geography", tags=["geography"])
reader = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


def _spatial(db: Session) -> bool:
    """True only on PostgreSQL/PostGIS; other dialects keep geometry as plain text."""
    return db.bind.dialect.name == "postgresql"


def _geojson(rows) -> list[dict]:
    return [{"id": row.id, "name": row.name, "geometry": json.loads(row[2])} for row in rows]


@router.get("/sectors", response_model=list[GeometryRead])
def list_sector_boundaries(db: Session = Depends(get_db), _: object = reader) -> list[dict]:
    if not _spatial(db):
        return []
    rows = db.execute(select(Sector.id, Sector.name, ST_AsGeoJSON(Sector.boundary)).where(Sector.boundary.is_not(None))).all()
    return _geojson(rows)


@router.get("/cells", response_model=list[GeometryRead])
def list_cell_boundaries(db: Session = Depends(get_db), _: object = reader) -> list[dict]:
    if not _spatial(db):
        return []
    rows = db.execute(select(Cell.id, Cell.name, ST_AsGeoJSON(Cell.boundary)).where(Cell.boundary.is_not(None)).order_by(Cell.name)).all()
    return _geojson(rows)


@router.get("/farmers")
def list_farmer_locations(db: Session = Depends(get_db), _: object = reader) -> list[dict]:
    if not _spatial(db):
        return []
    rows = db.execute(select(FieldUser.id, FieldUser.full_name, ST_AsGeoJSON(FieldUser.location)).where(FieldUser.role == UserRole.farmer, FieldUser.location.is_not(None))).all()
    return [{"id": row.id, "name": row.full_name or "Unnamed farmer", "geometry": json.loads(row[2])} for row in rows]
