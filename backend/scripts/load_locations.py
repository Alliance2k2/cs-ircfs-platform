"""Load Bugesera sectors and cells from data/*.gpkg using only the Python standard library.

Works on SQLite (centre points only) and PostgreSQL/PostGIS (centre points and boundaries),
so a demo machine does not need QGIS. Existing rows are matched by name and only missing
values are filled. Usage:  python scripts/load_locations.py
"""
import sqlite3
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make the `app` package importable

from sqlalchemy import func, select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.models import Cell, Sector  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "data"
ENVELOPE_BYTES = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}


def parse_gpkg_geometry(blob: bytes) -> tuple[bytes, float, float]:
    """Split a GeoPackage geometry into standard WKB and the centre of its envelope."""
    flags = blob[3]
    envelope_type = (flags >> 1) & 7
    order = "<" if flags & 1 else ">"
    header = 8 + ENVELOPE_BYTES[envelope_type]
    if envelope_type:
        min_x, max_x, min_y, max_y = struct.unpack(order + "4d", blob[8:40])
        centre = ((min_y + max_y) / 2, (min_x + max_x) / 2)
    else:
        centre = (None, None)
    return blob[header:], centre[0], centre[1]


def read_layer(path: Path, table: str, columns: str) -> list[tuple]:
    with sqlite3.connect(path) as gpkg:
        return gpkg.execute(f'SELECT {columns}, geom FROM "{table}"').fetchall()


def set_boundary(db: Session, table: str, row_id: int, wkb: bytes) -> None:
    if db.bind.dialect.name != "postgresql":
        return
    db.execute(text(f"UPDATE {table} SET boundary = ST_Multi(ST_CurveToLine(ST_GeomFromWKB(:wkb, 4326))) WHERE id = :id AND boundary IS NULL"),
               {"wkb": wkb, "id": row_id})


def load(db: Session) -> tuple[int, int]:
    sectors_added = cells_added = 0
    for (name, blob) in read_layer(DATA / "bugesera_sectors.gpkg", "sector_boundary", "sector"):
        wkb, lat, lng = parse_gpkg_geometry(blob)
        sector = db.scalar(select(Sector).where(func.lower(Sector.name) == name.lower()))
        if sector is None:
            sector = Sector(name=name)
            db.add(sector)
            sectors_added += 1
        if sector.latitude is None:
            sector.latitude, sector.longitude = lat, lng
        db.flush()
        set_boundary(db, "sectors", sector.id, wkb)
    sector_ids = {name.lower(): sector_id for sector_id, name in db.execute(select(Sector.id, Sector.name))}
    for (sector_name, name, blob) in read_layer(DATA / "bugesera_cells.gpkg", "cell_boundary", "sector, cell"):
        sector_id = sector_ids.get(sector_name.lower())
        if sector_id is None:
            continue
        wkb, lat, lng = parse_gpkg_geometry(blob)
        cell = db.scalar(select(Cell).where(Cell.sector_id == sector_id, func.lower(Cell.name) == name.lower()))
        if cell is None:
            cell = Cell(name=name, sector_id=sector_id)
            db.add(cell)
            cells_added += 1
        if cell.latitude is None:
            cell.latitude, cell.longitude = lat, lng
        db.flush()
        set_boundary(db, "cells", cell.id, wkb)
    db.commit()
    return sectors_added, cells_added


def main() -> None:
    with SessionLocal() as db:
        sectors, cells = load(db)
    print(f"Bugesera locations ready: {sectors} sectors and {cells} cells added (existing rows kept).")


if __name__ == "__main__":
    main()
