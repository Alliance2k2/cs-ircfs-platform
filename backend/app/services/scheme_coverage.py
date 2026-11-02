"""Scheme service areas, with compatibility for the original single-sector column."""
from fastapi import HTTPException
from sqlalchemy import delete, or_, select

from app.db.models import IrrigationScheme, SchemeSectorCoverage, Sector


def covering_sectors(sector_ids):
    return or_(IrrigationScheme.sector_id.in_(sector_ids), IrrigationScheme.id.in_(
        select(SchemeSectorCoverage.scheme_id).where(SchemeSectorCoverage.sector_id.in_(sector_ids))))


def sector_ids_for_scheme(db, scheme):
    sectors = set(db.scalars(select(SchemeSectorCoverage.sector_id).where(SchemeSectorCoverage.scheme_id == scheme.id)))
    if scheme.sector_id is not None:
        sectors.add(scheme.sector_id)
    return sorted(sectors)


def validate_sectors(db, sector_ids):
    if len(sector_ids) != len(set(sector_ids)):
        raise HTTPException(422, "Coverage sectors must not contain duplicates")
    known = set(db.scalars(select(Sector.id).where(Sector.id.in_(sector_ids))))
    if known != set(sector_ids):
        raise HTTPException(422, "Coverage contains an unknown sector")


def replace_coverage(db, scheme, sector_ids):
    validate_sectors(db, sector_ids)
    db.execute(delete(SchemeSectorCoverage).where(SchemeSectorCoverage.scheme_id == scheme.id))
    for sector_id in sector_ids:
        db.add(SchemeSectorCoverage(scheme_id=scheme.id, sector_id=sector_id))
    # Keep the legacy column a member of the service area for old clients.
    scheme.sector_id = scheme.sector_id if scheme.sector_id in sector_ids else next(iter(sector_ids), None)


def scheme_row(db, scheme):
    return {**{column.name: getattr(scheme, column.name) for column in IrrigationScheme.__table__.columns
               if column.name != "boundary"}, "coverage_sector_ids": sector_ids_for_scheme(db, scheme)}
