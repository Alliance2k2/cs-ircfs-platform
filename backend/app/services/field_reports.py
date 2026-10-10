"""Citizen field reports as one list: crop harvests, pest alerts, rainfall and asset checks.

Each row carries quality flags computed from the data itself, so officers can see at a
glance which reports need a closer look before they are trusted:

* ``no_location``     no cell and no coordinates: the report cannot be mapped,
* ``no_scheme``       not linked to an irrigation scheme,
* ``missing_measure`` the key value is absent (tons for a harvest, severity for a pest,
                      condition for an asset),
* ``unusual_value``   beyond a plausibility limit (rain over 150 mm in one reading,
                      over 50 t from one farmer),
* ``possible_duplicate`` the same phone sent the same kind of report with the same key
                      value in the previous 24 hours.

Flags are hints, not judgements: verification by an officer is what makes a report
verified. Simulator tests never appear here.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.privacy import mask_phone
from app.db.models import Cell, CitizenScienceLog, FieldUser, IncidentCase, IrrigationClimateLog, IrrigationScheme, Sector
from app.services.evidence import counted

KINDS = ("harvest", "pest", "rain", "asset")
RAIN_LIMIT_MM = 150
HARVEST_LIMIT_T = 50
DUPLICATE_WINDOW = timedelta(hours=24)
SOURCES = {"crop": CitizenScienceLog, "infrastructure": IrrigationClimateLog}


def aware(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


def classify(source: str, report) -> tuple[str, str, str]:
    """(kind, title, duplicate key)."""
    if source == "crop":
        if report.pest_or_disease:
            return "pest", f"{report.pest_or_disease} on {report.crop_type}", f"pest:{report.pest_or_disease}:{report.crop_type}".lower()
        return "harvest", f"{report.crop_type} harvest", f"harvest:{report.crop_type}".lower()
    if report.rainfall_mm is not None:
        return "rain", f"Rain gauge: {report.rainfall_mm:g} mm", f"rain:{report.rainfall_mm:g}"
    name = report.infrastructure_name or "Irrigation asset"
    return "asset", f"{name}: {report.operational_status or 'reported'}", f"asset:{name}:{report.operational_status}".lower()


def flags(source: str, kind: str, report) -> list[str]:
    found = []
    if report.cell_id is None and report.latitude is None:
        found.append("no_location")
    if report.scheme_id is None:
        found.append("no_scheme")
    if kind == "harvest" and report.expected_harvest_tons is None and report.reported_harvest_tons is None:
        found.append("missing_measure")
    if kind == "pest" and report.severity is None:
        found.append("missing_measure")
    if kind == "asset" and not report.operational_status:
        found.append("missing_measure")
    if kind == "rain" and report.rainfall_mm > RAIN_LIMIT_MM:
        found.append("unusual_value")
    if kind == "harvest" and max(report.expected_harvest_tons or 0, report.reported_harvest_tons or 0) > HARVEST_LIMIT_T:
        found.append("unusual_value")
    return found


class Lookup:
    """Names for cells, sectors, schemes and reporters, loaded once per request."""

    def __init__(self, db: Session):
        self.cells = {cell.id: cell for cell in db.scalars(select(Cell))}
        self.sectors = dict(db.execute(select(Sector.id, Sector.name)).all())
        self.schemes = dict(db.execute(select(IrrigationScheme.id, IrrigationScheme.name)).all())
        self.people = {person.id: person for person in db.scalars(select(FieldUser))}

    def sector_of(self, cell_id: int | None) -> tuple[int | None, str | None]:
        cell = self.cells.get(cell_id)
        return (cell.sector_id, self.sectors.get(cell.sector_id)) if cell else (None, None)


def row(source: str, report, lookup: Lookup, personal: bool, duplicate: bool) -> dict:
    kind, title, _ = classify(source, report)
    sector_id, sector = lookup.sector_of(report.cell_id)
    cell = lookup.cells.get(report.cell_id)
    person = lookup.people.get(report.reporter_id)
    found = flags(source, kind, report) + (["possible_duplicate"] if duplicate else [])
    return {
        "id": report.id, "source": source, "kind": kind, "title": title,
        "crop": getattr(report, "crop_type", None), "pest": getattr(report, "pest_or_disease", None), "severity": getattr(report, "severity", None),
        "expected_tons": getattr(report, "expected_harvest_tons", None), "reported_tons": getattr(report, "reported_harvest_tons", None),
        "rainfall_mm": getattr(report, "rainfall_mm", None), "asset": getattr(report, "infrastructure_name", None),
        "condition": getattr(report, "operational_status", None), "bottleneck": getattr(report, "bottleneck_category", None),
        "scheme_id": report.scheme_id, "scheme": lookup.schemes.get(report.scheme_id),
        "cell_id": report.cell_id, "cell": cell.name if cell else None, "sector_id": sector_id, "sector": sector,
        "reporter_id": report.reporter_id,
        "reporter": (person.phone_number if personal else mask_phone(person.phone_number)) if person else None,
        "reporter_role": person.role.value if person else None,
        "data_origin": report.data_origin, "verification_status": report.verification_status,
        "verified_at": report.verified_at, "verification_note": report.verification_note if personal else None,
        "flags": found, "created_at": report.created_at,
    }


def list_reports(db: Session, cells: set[int] | None, personal: bool, *, kind: str | None = None, days: int = 30,
                 sector_id: int | None = None, scheme_id: int | None = None, verification: str | None = None,
                 origin: str | None = None, limit: int = 500) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    lookup = Lookup(db)
    if sector_id is not None:
        sector_cells = {cell_id for cell_id, cell in lookup.cells.items() if cell.sector_id == sector_id}
        cells = sector_cells if cells is None else cells & sector_cells
    wanted_sources = {"harvest": ["crop"], "pest": ["crop"], "rain": ["infrastructure"], "asset": ["infrastructure"]}.get(kind or "", list(SOURCES))
    collected: list[tuple[str, object]] = []
    for source in wanted_sources:
        model = SOURCES[source]
        # Look back an extra day so duplicates of reports at the start of the window are found.
        query = select(model).where(counted(model), model.created_at >= since - DUPLICATE_WINDOW)
        if cells is not None:
            query = query.where(model.cell_id.in_(cells))
        if scheme_id is not None:
            query = query.where(model.scheme_id == scheme_id)
        if verification:
            query = query.where(model.verification_status == verification)
        if origin:
            query = query.where(model.data_origin == origin)
        collected += [(source, report) for report in db.scalars(query)]
    collected.sort(key=lambda item: (aware(item[1].created_at), item[1].id))

    last_seen: dict[tuple, datetime] = {}
    rows = []
    for source, report in collected:
        report_kind, _, key = classify(source, report)
        created = aware(report.created_at)
        signature = (report.reporter_id, key)
        duplicate = report.reporter_id is not None and signature in last_seen and created - last_seen[signature] <= DUPLICATE_WINDOW
        last_seen[signature] = created
        if created < since or (kind and report_kind != kind):
            continue
        rows.append(row(source, report, lookup, personal, duplicate))
    rows.sort(key=lambda item: aware(item["created_at"]), reverse=True)
    return rows[:limit]


def linked_case(db: Session, source: str, report_id: int) -> IncidentCase | None:
    return db.scalar(select(IncidentCase).where(IncidentCase.source_type == source, IncidentCase.source_id == report_id))
