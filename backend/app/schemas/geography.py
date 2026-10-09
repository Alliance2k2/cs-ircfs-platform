"""Geography and map data schemas."""
from pydantic import BaseModel


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


class GeometryRead(BaseModel):
    id: int
    name: str
    geometry: dict


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
    # Spatial overlays need PostGIS; local SQLite returns points only and the UI shows a notice.
    spatial_available: bool = True
