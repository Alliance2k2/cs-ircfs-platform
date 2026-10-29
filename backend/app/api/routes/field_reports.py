"""Citizen field reports: the unified list with quality flags, one report's detail,
verification by district staff, and a CSV export without personal data."""
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.csv_export import csv_download
from app.core.privacy import sees_personal_data
from app.core.scope import allowed_cells, check_cell
from app.core.security import Principal, require_roles
from app.db.models import ORIGIN_SIMULATOR, AuditEvent, UserRole
from app.db.session import get_db
from app.services.audit import record
from app.services.field_reports import KINDS, SOURCES, Lookup, linked_case, list_reports, row

router = APIRouter(prefix="/api/v1/field-reports", tags=["field reports"])
viewer = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
staff = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
Source = Literal["crop", "infrastructure"]


class VerificationUpdate(BaseModel):
    status: Literal["verified", "rejected", "unverified"]
    note: str | None = Field(default=None, max_length=1000)


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
               "cultivated_area_hectares", "yield_tons_per_hectare", "harvest_date", "season", "rainfall_mm", "asset",
               "condition", "bottleneck", "scheme", "sector", "cell", "data_origin", "verification_status", "flags", "created_at"]
    rows = [[";".join(item[column]) if column == "flags" else item[column] for column in columns] for item in reports]
    record(db, principal, "field_reports.export", "field_report", None, rows=len(rows), **{k: v for k, v in params.items() if v is not None})
    db.commit()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return csv_download(f"cs-ircfs-field-reports-{stamp}.csv", columns, rows)


def _note(detail: str | None) -> str | None:
    """The note recorded with a verification decision, from the audit detail."""
    try:
        return json.loads(detail).get("note") if detail else None
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
    report = find_report(db, source, report_id, principal)
    if payload.status == "rejected" and not (payload.note or "").strip():
        raise HTTPException(status_code=422, detail="Give a reason when rejecting a report")
    report.verification_status = payload.status
    report.verification_note = (payload.note or "").strip() or None
    report.verified_by_account_id = principal.account_id if payload.status != "unverified" else None
    report.verified_at = datetime.now(timezone.utc) if payload.status != "unverified" else None
    record(db, principal, f"report.{payload.status}", f"{source}_report", report.id, note=report.verification_note)
    db.commit()
    return {"id": report.id, "source": source, "verification_status": report.verification_status, "verified_at": report.verified_at}
