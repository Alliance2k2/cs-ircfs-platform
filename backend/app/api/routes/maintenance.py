"""Staff-recorded outages and append-only maintenance, using stable inventory asset IDs."""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells, check_cell
from app.core.security import Principal, require_roles
from app.db.models import AssetMaintenance, AssetOutage, UserRole
from app.db.session import get_db
from app.schemas.climate_maintenance import MaintenanceCreate, OutageCreate
from app.services.audit import record
from app.services.climate import KIGALI
from app.services.maintenance import maintenance_history, scoped_asset

router = APIRouter(prefix="/api/v1/irrigation", tags=["maintenance"])
viewer = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
staff = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.get("/maintenance")
def history(start: date | None = None, end: date | None = None, asset_id: int | None = Query(default=None, gt=0),
            db: Session = Depends(get_db), principal: Principal = viewer):
    end = end or datetime.now(KIGALI).date()
    return maintenance_history(db, principal, start or end - timedelta(days=89), end, asset_id)


@router.post("/outages", status_code=201)
def create_outage(payload: OutageCreate, db: Session = Depends(get_db), principal: Principal = staff):
    asset, location = scoped_asset(db, principal, payload.asset_id, payload.cell_id, lock=True)
    if not asset.is_active:
        raise HTTPException(422, "Asset is inactive")
    # Do not let demonstration records obstruct a real outage (or vice versa).
    origins = ("demo",) if payload.data_origin == "demo" else ("field", "import")
    overlap = db.scalar(select(AssetOutage.id).where(AssetOutage.asset_id == asset.id, AssetOutage.data_origin.in_(origins),
        (AssetOutage.ended_at.is_(None)) | (AssetOutage.ended_at > payload.started_at)))
    if overlap:
        raise HTTPException(409, "An overlapping outage already exists for this asset")
    outage = AssetOutage(**{**payload.model_dump(), "cell_id": location}, created_by_account_id=principal.account_id)
    db.add(outage)
    db.flush()
    record(db, principal, "outage.create", "asset_outage", outage.id, asset_id=asset.id, started_at=payload.started_at)
    db.commit()
    return {"id": outage.id, "repair_status": outage.repair_status}


@router.post("/maintenance", status_code=201)
def record_maintenance(payload: MaintenanceCreate, db: Session = Depends(get_db), principal: Principal = staff):
    asset, location = scoped_asset(db, principal, payload.asset_id, payload.cell_id, lock=True)
    outage = None
    if payload.outage_id:
        outage = db.scalar(select(AssetOutage).where(AssetOutage.id == payload.outage_id).with_for_update())
        if outage is None or outage.asset_id != asset.id:
            raise HTTPException(422, "Outage must belong to the selected asset")
        check_cell(outage.cell_id, allowed_cells(db, principal), "Outage")
        if outage.cell_id != location or (outage.data_origin == "demo") != (payload.data_origin == "demo"):
            raise HTTPException(422, "Maintenance must match outage location and evidence origin")
        if outage.ended_at is not None:
            raise HTTPException(409, "Outage already repaired; add independent preventive maintenance instead")
        if payload.performed_at < outage.started_at:
            raise HTTPException(422, "Maintenance cannot precede outage start")
        latest_event = db.scalar(select(AssetMaintenance.performed_at).where(AssetMaintenance.outage_id == outage.id)
                                 .order_by(AssetMaintenance.performed_at.desc()).limit(1))
        if payload.restored and latest_event and payload.performed_at < latest_event:
            raise HTTPException(422, "Repair completion cannot precede recorded outage inspections")
        if payload.restored:
            outage.ended_at = payload.performed_at
            outage.repair_status = "repaired"
        else:
            outage.repair_status = "in_progress"
    event = AssetMaintenance(**{**payload.model_dump(), "cell_id": location}, created_by_account_id=principal.account_id)
    db.add(event)
    db.flush()
    record(db, principal, "maintenance.record", "asset_maintenance", event.id, asset_id=asset.id,
           outage_id=payload.outage_id, restored=payload.restored, source=payload.source)
    db.commit()
    return {"id": event.id, "outage_id": payload.outage_id, "restored": payload.restored}
