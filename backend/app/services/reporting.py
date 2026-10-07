"""Shared report creation used by the REST API, the USSD menu, and SMS keywords.

Keeping this in one place guarantees that a report from a feature phone triggers the
same Act Now case rules as a report entered on the dashboard.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Cell, CitizenScienceLog, IncidentCase, IrrigationClimateLog, IrrigationScheme, User


def create_crop_report(db: Session, **values) -> CitizenScienceLog:
    report = CitizenScienceLog(**values)
    db.add(report)
    db.flush()
    severity = values.get("severity")
    if severity is not None and severity >= 4:
        db.add(IncidentCase(source_type="crop", source_id=report.id, priority="critical" if severity == 5 else "high"))
    return report


def create_irrigation_report(db: Session, **values) -> IrrigationClimateLog:
    report = IrrigationClimateLog(**values)
    db.add(report)
    db.flush()
    status = values.get("operational_status")
    if status in {"faulty", "offline"}:
        db.add(IncidentCase(source_type="irrigation", source_id=report.id, priority="critical" if status == "offline" else "high"))
    return report


def scheme_for_cell(db: Session, cell_id: int | None) -> int | None:
    """Link a report to the scheme serving its sector, so outcomes can be verified per scheme."""
    if cell_id is None:
        return None
    cell = db.get(Cell, cell_id)
    if not cell:
        return None
    return db.scalar(select(IrrigationScheme.id).where(IrrigationScheme.sector_id == cell.sector_id).order_by(IrrigationScheme.id).limit(1))


def scheme_by_prefix(db: Session, prefix: str) -> int | None:
    return db.scalar(select(IrrigationScheme.id).where(IrrigationScheme.name.ilike(f"{prefix}%")).order_by(IrrigationScheme.id).limit(1))


def find_or_register_user(db: Session, phone_number: str) -> User:
    """A first-time caller is registered as a farmer, keyed by phone number (architecture Section 7)."""
    user = db.scalar(select(User).where(User.phone_number == phone_number))
    if user is None:
        user = User(phone_number=phone_number)
        db.add(user)
        db.flush()
    return user
