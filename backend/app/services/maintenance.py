"""Scope-aware maintenance history and clipped recorded downtime; no inferred repairs."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select

from app.core.privacy import sees_personal_data
from app.core.scope import allowed_cells, check_cell
from app.db.models import AssetMaintenance, AssetOutage, Cell, IrrigationScheme, SchemeAsset
from app.services.climate import KIGALI, validate_window
from app.services.evidence import counted


def scoped_asset(db, principal, asset_id, cell_id=None, lock=False):
    query = select(SchemeAsset).where(SchemeAsset.id == asset_id)
    asset = db.scalar(query.with_for_update() if lock else query)
    if asset is None:
        raise HTTPException(404, "Inventory asset not found")
    check_cell(asset.cell_id, allowed_cells(db, principal), "Asset")
    if cell_id is not None and db.get(Cell, cell_id) is None:
        raise HTTPException(422, "Unknown cell")
    if asset.cell_id is not None and cell_id is not None and asset.cell_id != cell_id:
        raise HTTPException(422, "Event cell must match the asset's verified location")
    location = asset.cell_id if asset.cell_id is not None else cell_id
    check_cell(location, allowed_cells(db, principal), "Asset")
    return asset, location


def interval_hours(outages, start, end):
    """Union of clipped explicit intervals, robust to imported overlapping records."""
    intervals = sorted((max(o.started_at, start), min(o.ended_at or end, end)) for o in outages
                       if o.started_at < end and (o.ended_at is None or o.ended_at > start))
    merged = []
    for left, right in intervals:
        if right <= left:
            continue
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else:
            merged.append((left, right))
    return round(sum((right - left).total_seconds() for left, right in merged) / 3600, 3)


def maintenance_history(db, principal, start, end, asset_id=None):
    validate_window(start, end)
    cells = allowed_cells(db, principal)
    query = select(SchemeAsset)
    if cells is not None:
        query = query.where(SchemeAsset.cell_id.in_(cells))
    if asset_id:
        scoped_asset(db, principal, asset_id)
        query = query.where(SchemeAsset.id == asset_id)
    start_at = datetime.combine(start, datetime.min.time(), tzinfo=KIGALI).astimezone(timezone.utc)
    end_at = min(datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=KIGALI).astimezone(timezone.utc), datetime.now(timezone.utc))
    schemes = dict(db.execute(select(IrrigationScheme.id, IrrigationScheme.name)).all())
    rows = []
    personal = sees_personal_data(principal)
    for asset in db.scalars(query.order_by(SchemeAsset.name_en)):
        outages = list(db.scalars(select(AssetOutage).where(AssetOutage.asset_id == asset.id, counted(AssetOutage),
            AssetOutage.started_at < end_at, (AssetOutage.ended_at.is_(None)) | (AssetOutage.ended_at > start_at))))
        events = list(db.scalars(select(AssetMaintenance).where(AssetMaintenance.asset_id == asset.id, counted(AssetMaintenance),
            AssetMaintenance.performed_at >= start_at, AssetMaintenance.performed_at < end_at).order_by(AssetMaintenance.performed_at.desc())))
        if cells is not None:
            outages = [o for o in outages if o.cell_id in cells]
            events = [e for e in events if e.cell_id in cells]
        rows.append({"id": asset.id, "name": asset.name_en, "scheme_id": asset.scheme_id, "scheme": schemes.get(asset.scheme_id), "cell_id": asset.cell_id,
                     "recorded_downtime_hours": interval_hours(outages, start_at, end_at) if outages else None,
                     "outage_count": len(outages), "open_outages": sum(o.ended_at is None for o in outages),
                     "recurrent_categories": sorted({o.category for o in outages if sum(x.category == o.category for x in outages) >= 3}),
                     "outages": [{"id": o.id, "started_at": o.started_at, "ended_at": o.ended_at, "category": o.category,
                         "repair_status": o.repair_status, "source": o.source, "description": o.description if personal else None} for o in outages],
                     "maintenance": [{"id": e.id, "outage_id": e.outage_id, "performed_at": e.performed_at, "kind": e.kind,
                         "action": e.action if personal else None, "source": e.source, "restored": e.restored} for e in events]})
    return {"start": start, "end": end, "as_of": end_at, "assets": rows,
            "method": "Recorded outage intervals only, clipped to this period; overlapping intervals counted once. Open intervals run to as_of. No records means unknown, not zero downtime or complete monitoring."}
