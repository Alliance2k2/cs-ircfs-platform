"""Uncapped daily measurements, coverage, and strictly comparable historical references."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from math import isfinite

from fastapi import HTTPException
from sqlalchemy import and_, or_, select

from app.core.scope import allowed_cells
from app.db.models import Cell, IrrigationClimateLog, IrrigationScheme, RainfallReference, Sector
from app.services.evidence import counted

KIGALI = timezone(timedelta(hours=2))


def validate_window(start: date, end: date):
    if end < start or (end - start).days >= 366 or end > datetime.now(KIGALI).date():
        raise HTTPException(422, "Choose a past/current interval of 1 to 366 days")


def observed_day(report):
    created = report.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return report.observation_date or created.astimezone(KIGALI).date()


def daily_summary(reports, start: date, end: date):
    days = [start + timedelta(days=n) for n in range((end - start).days + 1)]
    latest = {}
    unknown = 0
    for report in reports:
        mm = report.rainfall_mm
        if mm is None or not isfinite(mm) or mm < 0 or report.verification_status == "rejected":
            continue
        day = observed_day(report)
        if not start <= day <= end:
            continue
        if report.gauge_code:
            gauge = ("gauge", report.gauge_code, report.cell_id)
        elif report.reporter_id is not None:
            gauge = ("reporter", report.reporter_id, report.cell_id)
        else:
            unknown += 1
            continue
        # Newest daily submission replaces an earlier one; daily rain is not summed twice.
        stamp = report.created_at.replace(tzinfo=timezone.utc) if report.created_at.tzinfo is None else report.created_at
        key = (gauge, day)
        if key not in latest or (stamp, report.id) > latest[key][0]:
            latest[key] = ((stamp, report.id), report)
    gauges = {key[0] for key in latest}
    verified = {key: report for key, (_, report) in latest.items()
                if report.verification_status == "verified" and report.observation_date is not None and (report.data_source or "").strip()}
    complete = [g for g in gauges if all((g, day) in verified for day in days)]
    daily = []
    for day in days:
        readings = [r for (_, d), (_, r) in latest.items() if d == day]
        daily.append({"date": day, "mean_mm": round(sum(r.rainfall_mm for r in readings) / len(readings), 3) if readings else None,
                      "gauges": len(readings), "verified_gauges": sum(1 for g in gauges if (g, day) in verified)})
    observed = [item["mean_mm"] for item in daily if item["mean_mm"] is not None]
    complete_total = (sum(sum(verified[(g, day)].rainfall_mm for day in days) for g in complete) / len(complete)) if complete else None
    expected = len(gauges) * len(days)
    return {"daily": daily, "observed_days": len(observed), "missing_days": len(days) - len(observed),
            "gauges": len(gauges), "complete_verified_gauges": len(complete), "unknown_gauge_reports": unknown,
            "coverage_percent": round(100 * len(latest) / expected, 1) if expected else None,
            "partial_total_mm": round(sum(observed), 3) if observed else None,
            "verified_complete_total_mm": round(complete_total, 3) if complete_total is not None else None,
            "legacy_date_reports": sum(1 for _, report in latest.values() if report.observation_date is None),
            "method": "Daily mean across identified reporting gauges; missing days are null. Complete verified gauge totals only enter anomalies. Coverage is relative to gauges observed in this window, not all district gauges."}


def rainfall_analysis(db, principal, start, end, sector_id=None, scheme_id=None, reference_id=None):
    validate_window(start, end)
    if sector_id and scheme_id:
        raise HTTPException(422, "Select a sector or scheme, not both")
    if sector_id and db.get(Sector, sector_id) is None or scheme_id and db.get(IrrigationScheme, scheme_id) is None:
        raise HTTPException(404, "Location not found")
    cells = allowed_cells(db, principal)
    if sector_id:
        sector_cells = set(db.scalars(select(Cell.id).where(Cell.sector_id == sector_id)))
        if principal.sector_ids is not None and sector_id not in principal.sector_ids:
            raise HTTPException(404, "Sector not found")
        cells = sector_cells if cells is None else cells & sector_cells
    query = select(IrrigationClimateLog).where(counted(IrrigationClimateLog), IrrigationClimateLog.rainfall_mm.is_not(None))
    if cells is not None:
        query = query.where(IrrigationClimateLog.cell_id.in_(cells))
    if scheme_id:
        query = query.where(IrrigationClimateLog.scheme_id == scheme_id)
    query_start = min(start, end - timedelta(days=6))
    query = query.where(or_(IrrigationClimateLog.observation_date.between(query_start, end), and_(
        IrrigationClimateLog.observation_date.is_(None),
        IrrigationClimateLog.created_at >= datetime.combine(query_start, datetime.min.time(), tzinfo=KIGALI).astimezone(timezone.utc),
        IrrigationClimateLog.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=KIGALI).astimezone(timezone.utc))))
    # Observation date can precede receipt: filter using observation day, not ingestion timestamp.
    all_reports = list(db.scalars(query))
    reports = [r for r in all_reports if start <= observed_day(r) <= end]
    summary = daily_summary(reports, start, end)
    anomaly = {"status": "missing_reference", "difference_mm": None, "percent": None, "reference": None}
    if reference_id:
        ref = db.get(RainfallReference, reference_id)
        if ref is None:
            raise HTTPException(404, "Reference not found")
        if principal.sector_ids is not None:
            ref_sector = ref.sector_id or (db.get(IrrigationScheme, ref.scheme_id).sector_id if ref.scheme_id else None)
            if ref_sector not in principal.sector_ids:
                raise HTTPException(404, "Reference not found")
        if (ref.sector_id, ref.scheme_id, ref.period_start, ref.period_end) != (sector_id, scheme_id, start, end):
            anomaly["status"] = "reference_location_or_period_mismatch"
        elif principal.sector_ids is not None and scheme_id:
            anomaly["status"] = "sector_scope_cannot_verify_scheme_total"
        elif not ref.approved_at or ref.data_origin not in ("field", "import"):
            anomaly["status"] = "reference_not_approved"
        elif summary["verified_complete_total_mm"] is None:
            anomaly["status"] = "incomplete_verified_observations"
        else:
            delta = summary["verified_complete_total_mm"] - ref.mean_rainfall_mm
            anomaly.update(status="comparable" if ref.mean_rainfall_mm > 0 else "zero_reference",
                           difference_mm=round(delta, 3), percent=round(100 * delta / ref.mean_rainfall_mm, 2) if ref.mean_rainfall_mm > 0 else None)
        anomaly["reference"] = {"id": ref.id, "mean_rainfall_mm": ref.mean_rainfall_mm, "source": ref.source,
                                "document_reference": ref.document_reference, "reference_start_year": ref.reference_start_year,
                                "reference_end_year": ref.reference_end_year, "approved_at": ref.approved_at}
    cell_sectors = dict(db.execute(select(Cell.id, Cell.sector_id)).all())
    sectors = dict(db.execute(select(Sector.id, Sector.name)).all())
    schemes = dict(db.execute(select(IrrigationScheme.id, IrrigationScheme.name)).all())
    groups = {}
    for label, key, names in (("by_sector", lambda r: cell_sectors.get(r.cell_id), sectors), ("by_scheme", lambda r: r.scheme_id, schemes)):
        buckets = defaultdict(list)
        for report in reports:
            buckets[key(report)].append(report)
        groups[label] = [{"id": group_id, "name": names.get(group_id, "Unassigned"),
                          **{k: v for k, v in daily_summary(rows, start, end).items() if k != "daily"}}
                         for group_id, rows in buckets.items()]
    return {"start": start, "end": end, "sector_id": sector_id, "scheme_id": scheme_id,
            "summary": summary, "seven_day": daily_summary(all_reports, end - timedelta(days=6), end), "anomaly": anomaly, **groups, "generated_at": datetime.now(timezone.utc)}
