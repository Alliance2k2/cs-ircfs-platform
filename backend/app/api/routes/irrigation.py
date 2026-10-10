"""Irrigation command centre: every named asset's current condition, and one asset's history.

"Current" means the latest condition report for that asset (scheme + name). Counting
every fault ever reported would keep a repaired pump on the "down" list forever.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells
from app.core.security import Principal, require_roles
from app.db.models import Cell, IncidentCase, IrrigationClimateLog, IrrigationScheme, SchemeAsset, Sector, UserRole
from app.db.session import get_db
from app.services.analytics import ACTIVE, latest_asset_status
from app.services.evidence import counted

router = APIRouter(prefix="/api/v1/irrigation", tags=["irrigation command centre"])
viewer = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


def names(db: Session) -> tuple[dict, dict]:
    sectors = dict(db.execute(select(Cell.id, Sector.name).join(Sector, Sector.id == Cell.sector_id)).all())
    schemes = dict(db.execute(select(IrrigationScheme.id, IrrigationScheme.name)).all())
    return sectors, schemes


def asset_reports(db: Session, scheme_id: int | None, asset: str, cells: set[int] | None):
    query = (select(IrrigationClimateLog)
             .where(counted(IrrigationClimateLog), IrrigationClimateLog.infrastructure_name.is_not(None))
             .order_by(IrrigationClimateLog.created_at.desc(), IrrigationClimateLog.id.desc()))
    query = query.where(IrrigationClimateLog.scheme_id == scheme_id) if scheme_id is not None else query.where(IrrigationClimateLog.scheme_id.is_(None))
    if cells is not None:
        query = query.where(IrrigationClimateLog.cell_id.in_(cells))
    key = asset.strip().lower()
    return [report for report in db.scalars(query) if report.infrastructure_name.strip().lower() == key]


@router.get("/assets")
def assets(scheme_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db), principal: Principal = viewer) -> dict:
    """Each named asset with its latest condition, report count, open cases and the registered inventory."""
    cells = allowed_cells(db, principal)
    sectors, schemes = names(db)
    rows = []
    for asset in latest_asset_status(db, cells, scheme_id):
        reports = asset_reports(db, asset["scheme_id"], asset["asset"], cells)
        report_ids = [report.id for report in reports]
        open_cases = db.scalars(select(IncidentCase).where(IncidentCase.source_type == "infrastructure", IncidentCase.source_id.in_(report_ids),
                                                           IncidentCase.status.in_(ACTIVE))).all() if report_ids else []
        faults = [report for report in reports if report.operational_status in ("faulty", "offline")]
        rows.append({**asset, "scheme": schemes.get(asset["scheme_id"]), "sector": sectors.get(asset["cell_id"]),
                     "reports": len(reports), "fault_reports": len(faults),
                     "open_cases": [{"id": case.id, "priority": case.priority, "status": case.status.value} for case in open_cases]})
    inventory = db.scalars(select(SchemeAsset).where(SchemeAsset.is_active.is_(True)).order_by(SchemeAsset.id))
    reported = {(row["scheme_id"], row["asset"].strip().lower()) for row in rows}
    never_reported = [{"asset": item.name_en, "scheme_id": item.scheme_id, "scheme": schemes.get(item.scheme_id), "asset_type": item.asset_type}
                      for item in inventory if (item.scheme_id, item.name_en.strip().lower()) not in reported]
    return {"assets": rows, "never_reported": never_reported,
            "counts": {"assets": len(rows), "down": sum(1 for row in rows if row["down"]), "open_cases": sum(len(row["open_cases"]) for row in rows)}}


@router.get("/assets/history")
def asset_history(asset: str = Query(min_length=1, max_length=120), scheme_id: int | None = Query(default=None, gt=0),
                  db: Session = Depends(get_db), principal: Principal = viewer) -> dict:
    """Every condition report for one asset, newest first, with the cases they opened."""
    cells = allowed_cells(db, principal)
    reports = asset_reports(db, scheme_id, asset, cells)
    if not reports:
        raise HTTPException(status_code=404, detail="No condition reports for this asset")
    sectors, schemes = names(db)
    cases = {case.source_id: case for case in db.scalars(select(IncidentCase).where(
        IncidentCase.source_type == "infrastructure", IncidentCase.source_id.in_([report.id for report in reports])))}
    return {
        "asset": reports[0].infrastructure_name, "scheme_id": scheme_id, "scheme": schemes.get(scheme_id),
        "latitude": next((report.latitude for report in reports if report.latitude is not None), None),
        "longitude": next((report.longitude for report in reports if report.longitude is not None), None),
        "history": [{"id": report.id, "condition": report.operational_status, "bottleneck": report.bottleneck_category,
                     "description": report.fault_description, "sector": sectors.get(report.cell_id), "data_origin": report.data_origin,
                     "verification_status": report.verification_status, "created_at": report.created_at,
                     "case": ({"id": cases[report.id].id, "priority": cases[report.id].priority, "status": cases[report.id].status.value}
                              if report.id in cases else None)} for report in reports],
    }
