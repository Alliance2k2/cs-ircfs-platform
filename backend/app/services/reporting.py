"""Shared report creation used by the REST API, the USSD menu, and SMS keywords.

Keeping this in one place guarantees that a report from a feature phone triggers the
same Act Now case rules as a report entered on the dashboard.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Cell, CitizenScienceLog, IncidentCase, IrrigationClimateLog, IrrigationScheme, User


def open_case(db: Session, source_type: str, report, priority: str, summary: str) -> IncidentCase:
    """Create an Act Now case and alert district staff by SMS when it is urgent enough."""
    from app.services.notifications import alert_staff  # notifications imports sms; keep reporting import-light

    case = IncidentCase(source_type=source_type, source_id=report.id, priority=priority)
    db.add(case)
    db.flush()
    alert_staff(db, case, summary, report.cell_id)
    return case


def create_crop_report(db: Session, **values) -> CitizenScienceLog:
    report = CitizenScienceLog(**values)
    db.add(report)
    db.flush()
    severity = values.get("severity")
    if severity is not None and severity >= 4:
        summary = f"{report.pest_or_disease or 'Pest or disease'} on {report.crop_type}, severity {severity}"
        open_case(db, "crop", report, "critical" if severity == 5 else "high", summary)
    return report


def create_irrigation_report(db: Session, **values) -> IrrigationClimateLog:
    report = IrrigationClimateLog(**values)
    db.add(report)
    db.flush()
    status = values.get("operational_status")
    if status in {"faulty", "offline"}:
        summary = f"{report.infrastructure_name or 'Irrigation asset'} is {status}" + (f" ({report.bottleneck_category})" if report.bottleneck_category else "")
        open_case(db, "irrigation", report, "critical" if status == "offline" else "high", summary)
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
