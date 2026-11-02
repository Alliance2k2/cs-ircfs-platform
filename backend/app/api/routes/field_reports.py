"""Citizen field reports: the unified list with quality flags, one report's detail,
verification by district staff, and a CSV export without personal data."""
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.csv_export import csv_download
from app.core.privacy import sees_personal_data
from app.core.scope import allowed_cells, check_cell
from app.core.security import Principal, require_roles
from app.db.models import ORIGIN_SIMULATOR, AuditEvent, UserRole
from app.db.session import get_db
from app.services.audit import record
from app.services.field_reports import KINDS, SOURCES, Lookup, linked_case, list_reports, row
from app.schemas.reports import CropReportCreate, IrrigationReportCreate
from app.services.references import validate_report_references, validate_report_scope

router = APIRouter(prefix="/api/v1/field-reports", tags=["field reports"])
viewer = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
staff = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
Source = Literal["crop", "infrastructure"]


class VerificationUpdate(BaseModel):
    status: Literal["verified", "rejected", "unverified"]
    note: str | None = Field(default=None, max_length=1000)


class ReportCorrection(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
    changes: dict


def filters(
    kind: Literal["harvest", "pest", "rain", "asset"] | None = None,
    days: int = Query(default=30, ge=1, le=365),
    sector_id: int | None = Query(default=None, gt=0),
    scheme_id: int | None = Query(default=None, gt=0),
    verification: Literal["unverified", "verified", "rejected"] | None = None,
    origin: Literal["field", "demo", "import"] | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return {"kind": kind, "days": days, "sector_id": sector_id, "scheme_id": scheme_id,
            "verification": verification, "origin": origin, "limit": limit, "offset": offset}


@router.get("")
def field_reports(params: dict = Depends(filters), db: Session = Depends(get_db), principal: Principal = viewer) -> dict:
    """Reports in the person's area, newest first (at most 500), each with its quality flags.

    Monitors and cooperative leaders see masked phone numbers and no verification notes.
    """
    limit = params["limit"]
    offset = params["offset"]
    rows = list_reports(db, allowed_cells(db, principal), sees_personal_data(principal),
                        **{**params, "limit": limit + 1})
    truncated = len(rows) > limit
    rows = rows[:limit]
    return {"reports": rows, "kinds": list(KINDS), "personal_data": sees_personal_data(principal),
            "truncated": truncated, "offset": offset, "next_offset": offset + len(rows) if truncated else None}


def find_report(db: Session, source: str, report_id: int, principal: Principal):
    report = db.get(SOURCES[source], report_id)
    if report is None or report.data_origin == ORIGIN_SIMULATOR:
        raise HTTPException(status_code=404, detail="Report not found")
    check_cell(report.cell_id, allowed_cells(db, principal), "Report")
    return report


@router.get("/export.csv")
def export_reports(params: dict = Depends(filters), db: Session = Depends(get_db), principal: Principal = staff) -> StreamingResponse:
    """The filtered list as CSV for analysis. No names or phone numbers are included."""
    export_params = {key: value for key, value in params.items() if key not in {"limit", "offset"}}
    reports = list_reports(db, allowed_cells(db, principal), False, **export_params, limit=500)
    columns = ["id", "source", "kind", "title", "crop", "pest", "severity", "expected_tons", "reported_tons",
               "cultivated_area_hectares", "harvested_area_hectares", "yield_tons_per_hectare", "harvest_date", "season",
               "reference_year", "observation_type", "data_source", "superseded_by_id", "rainfall_mm", "asset",
               "condition", "bottleneck", "scheme", "sector", "cell", "data_origin", "verification_status", "flags", "created_at"]
    rows = [[";".join(item[column]) if column == "flags" else item[column] for column in columns] for item in reports]
    record(db, principal, "field_reports.export", "field_report", None, rows=len(rows), **{k: v for k, v in params.items() if v is not None})
    db.commit()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return csv_download(f"cs-ircfs-field-reports-{stamp}.csv", columns, rows)


def _note(detail: str | None) -> str | None:
    """The note recorded with a verification decision, from the audit detail."""
    try:
        return (json.loads(detail).get("note") or json.loads(detail).get("reason")) if detail else None
    except (ValueError, AttributeError):
        return None


@router.get("/{source}/{report_id}")
def field_report(source: Source, report_id: int, db: Session = Depends(get_db), principal: Principal = viewer) -> dict:
    """One report with its linked case and verification history."""
    report = find_report(db, source, report_id, principal)
    personal = sees_personal_data(principal)
    detail = row(source, report, Lookup(db), personal, duplicate=False)
    detail["notes"] = (getattr(report, "notes", None) or getattr(report, "fault_description", None)) if personal else None
    detail["latitude"], detail["longitude"] = report.latitude, report.longitude
    case = linked_case(db, source, report.id)
    detail["case"] = {"id": case.id, "priority": case.priority, "status": case.status.value} if case else None
    history = db.scalars(select(AuditEvent).where(AuditEvent.entity == f"{source}_report", AuditEvent.entity_id == report.id)
                         .order_by(AuditEvent.id.desc())) if personal else []
    detail["verification_history"] = [{"action": event.action, "by": event.actor_label, "detail": _note(event.detail), "at": event.created_at} for event in history]
    return detail


@router.patch("/{source}/{report_id}/verification")
def verify_report(source: Source, report_id: int, payload: VerificationUpdate, db: Session = Depends(get_db), principal: Principal = staff) -> dict:
    """Mark a report verified or rejected (with a note), or return it to unverified."""
    model = SOURCES[source]
    db.scalar(select(model).where(model.id == report_id).with_for_update().execution_options(populate_existing=True))
    report = find_report(db, source, report_id, principal)
    if report.superseded_by_id is not None:
        raise HTTPException(409, "This report was superseded; verify the replacement instead")
    if payload.status == "rejected" and not (payload.note or "").strip():
        raise HTTPException(status_code=422, detail="Give a reason when rejecting a report")
    report.verification_status = payload.status
    report.verification_note = (payload.note or "").strip() or None
    report.verified_by_account_id = principal.account_id if payload.status != "unverified" else None
    report.verified_at = datetime.now(timezone.utc) if payload.status != "unverified" else None
    record(db, principal, f"report.{payload.status}", f"{source}_report", report.id, note=report.verification_note)
    db.commit()
    return {"id": report.id, "source": source, "verification_status": report.verification_status, "verified_at": report.verified_at}


@router.post("/{source}/{report_id}/corrections", status_code=201)
def correct_report(source: Source, report_id: int, payload: ReportCorrection,
                   db: Session = Depends(get_db), principal: Principal = staff) -> dict:
    original = find_report(db, source, report_id, principal)
    if not payload.reason.strip() or not payload.changes:
        raise HTTPException(422, "A correction requires changed values and a reason")
    schema = CropReportCreate if source == "crop" else IrrigationReportCreate
    if set(payload.changes) - schema.model_fields.keys():
        raise HTTPException(422, "Only report measurement and location fields can be corrected")
    model = SOURCES[source]
    db.scalar(select(model).where(model.id == report_id).with_for_update().execution_options(populate_existing=True))
    if original.superseded_by_id is not None:
        raise HTTPException(409, "Report already superseded")
    values = {name: getattr(original, name) for name in schema.model_fields}
    values.update(payload.changes)
    try:
        validated = schema.model_validate(values)
    except ValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    validate_report_scope(db, principal, validated)
    validate_report_references(db, validated.reporter_id, validated.scheme_id, validated.cell_id)
    if validated.model_dump() == {name: getattr(original, name) for name in schema.model_fields}:
        raise HTTPException(422, "Correction does not change the report")
    replacement = model(**validated.model_dump(), data_origin=original.data_origin,
                        correction_reason=payload.reason.strip(), created_at=original.created_at)
    db.add(replacement)
    db.flush()
    result = db.execute(update(model).where(model.id == report_id, model.superseded_by_id.is_(None))
                        .values(superseded_by_id=replacement.id).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Report was concurrently corrected")
    case = linked_case(db, source, report_id)
    if case:
        # Keep the existing follow-up workflow and history; do not send fresh alerts.
        check_cell(original.cell_id, allowed_cells(db, principal), "Report")
        case.source_id = replacement.id
    record(db, principal, "report.corrected", f"{source}_report", original.id,
           replacement_id=replacement.id, reason=payload.reason.strip(), changed_fields=sorted(payload.changes))
    record(db, principal, "report.correction_created", f"{source}_report", replacement.id,
           original_id=original.id, reason=payload.reason.strip())
    db.commit()
    return {"id": replacement.id, "source": source, "original_id": original.id, "verification_status": "unverified"}
