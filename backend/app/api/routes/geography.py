from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.functions import ST_AsGeoJSON, ST_GeomFromGeoJSON
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import Farm, Sector, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/geography", tags=["geography"])
planner = Depends(require_roles(UserRole.district_planner, UserRole.administrator))
reader = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


class FarmCreate(BaseModel):
    farmer_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=120)
    boundary: dict


class GeometryRead(BaseModel):
    id: int
    name: str
    geometry: dict


@router.post("/farms", status_code=status.HTTP_201_CREATED)
def create_farm(payload: FarmCreate, db: Session = Depends(get_db), _: object = planner) -> dict:
    if db.bind.dialect.name != "postgresql":
        raise HTTPException(status_code=501, detail="Farm geometry requires PostgreSQL/PostGIS")
    farmer = db.scalar(select(User).where(User.id == payload.farmer_id, User.role == UserRole.farmer))
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    farm = Farm(farmer_id=payload.farmer_id, name=payload.name, boundary=ST_GeomFromGeoJSON(payload.boundary))
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return {"id": farm.id, "farmer_id": farm.farmer_id, "name": farm.name}


@router.get("/farms", response_model=list[GeometryRead])
def list_farms(db: Session = Depends(get_db), _: object = reader) -> list[dict]:
    if db.bind.dialect.name != "postgresql":
        raise HTTPException(status_code=501, detail="Farm geometry requires PostgreSQL/PostGIS")
    rows = db.execute(select(Farm.id, Farm.name, ST_AsGeoJSON(Farm.boundary))).all()
    return [{"id": row.id, "name": row.name, "geometry": __import__("json").loads(row[2])} for row in rows]


@router.get("/sectors", response_model=list[GeometryRead])
def list_sector_boundaries(db: Session = Depends(get_db), _: object = reader) -> list[dict]:
    if db.bind.dialect.name != "postgresql":
        raise HTTPException(status_code=501, detail="Boundary geometry requires PostgreSQL/PostGIS")
    rows = db.execute(select(Sector.id, Sector.name, ST_AsGeoJSON(Sector.boundary)).where(Sector.boundary.is_not(None))).all()
    return [{"id": row.id, "name": row.name, "geometry": __import__("json").loads(row[2])} for row in rows]


@router.get("/farmers")
def list_farmer_locations(db: Session = Depends(get_db), _: object = reader) -> list[dict]:
    if db.bind.dialect.name != "postgresql":
        raise HTTPException(status_code=501, detail="Farmer geometry requires PostgreSQL/PostGIS")
    rows = db.execute(select(User.id, User.full_name, ST_AsGeoJSON(User.location)).where(User.role == UserRole.farmer, User.location.is_not(None))).all()
    return [{"id": row.id, "name": row.full_name or "Unnamed farmer", "geometry": __import__("json").loads(row[2])} for row in rows]
