"""Comparable verified sample yields. Never infer areas or approve legacy targets."""
from collections import Counter
from math import isfinite
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CitizenScienceLog, SchemeBaseline

FORMULA = "100 × verified observed tonnes/hectare ÷ approved target tonnes/hectare"


def tonnes(quantity: float, unit: str) -> float:
    if unit not in ("t", "kg") or not isfinite(quantity) or quantity < 0:
        raise ValueError("Harvest must be finite, non-negative and measured in t or kg")
    return quantity / 1000 if unit == "kg" else quantity


def target_tonnes(baseline: SchemeBaseline) -> float:
    return tonnes(baseline.expected_yield, {"t/ha": "t", "kg/ha": "kg"}[baseline.yield_unit])


def exclusion(report, baseline=None) -> str | None:
    if report.data_origin not in ("field", "import"):
        return "demonstration_or_simulator"
    if report.superseded_by_id is not None:
        return "superseded"
    if report.verification_status != "verified":
        return "not_verified"
    if report.observation_type != "measured" or not (report.data_source or "").strip():
        return "missing_measured_source"
    if report.harvest_date is None or report.harvest_date > datetime.now(timezone(timedelta(hours=2))).date():
        return "missing_harvest_date"
    area = report.harvested_area_hectares
    quantity = report.reported_harvest_tons
    if area is None or not isfinite(area) or area <= 0:
        return "missing_or_invalid_harvested_area"
    if report.cultivated_area_hectares is not None and (not isfinite(report.cultivated_area_hectares) or area > report.cultivated_area_hectares):
        return "inconsistent_area"
    if report.observed_quantity is not None:
        try:
            canonical = tonnes(report.observed_quantity, report.harvest_unit)
        except ValueError:
            return "invalid_measurement_unit"
        if quantity is None or abs(canonical - quantity) > 1e-9:
            return "inconsistent_quantity"
    if quantity is None or not isfinite(quantity) or quantity < 0:
        return "missing_or_invalid_observed_quantity"
    if not report.season or report.reference_year is None:
        return "missing_season_or_year"
    if report.pest_or_disease:
        return "pest_report"
    if baseline and (report.scheme_id != baseline.scheme_id
                     or report.crop_type.strip().casefold() != baseline.crop_type.strip().casefold()
                     or report.season.strip().casefold() != baseline.season.strip().casefold()
                     or report.reference_year != baseline.reference_year):
        return "crop_season_or_year_mismatch"
    return None


def approved_baselines(db: Session, scheme_id: int) -> list[SchemeBaseline]:
    rows = list(db.scalars(select(SchemeBaseline).where(SchemeBaseline.scheme_id == scheme_id)))
    # A replacement only retires its predecessor once approved; draft imports do not.
    approved = [b for b in rows if b.verification_status == "verified" and b.approved_at
                and b.data_origin in ("field", "import") and b.official_source.strip()
                and b.document_reference.strip() and b.yield_unit in ("t/ha", "kg/ha")
                and isfinite(b.expected_yield) and b.expected_yield > 0]
    retired = {b.supersedes_id for b in approved if b.supersedes_id}
    return [b for b in approved if b.id not in retired]


def compare(baseline: SchemeBaseline, reports: list) -> dict:
    eligible = [r for r in reports if exclusion(r, baseline) is None]
    area = sum(r.harvested_area_hectares for r in eligible)
    total = sum(r.reported_harvest_tons for r in eligible)
    observed = total / area if area > 0 else None
    target = target_tonnes(baseline)
    return {"baseline_id": baseline.id, "crop": baseline.crop_type, "season": baseline.season,
            "reference_year": baseline.reference_year, "source": baseline.official_source,
            "document_reference": baseline.document_reference, "target_tons_per_hectare": target,
            "observed_tons_per_hectare": round(observed, 6) if observed is not None else None,
            "observed_tons": total, "harvested_area_hectares": area, "eligible_reports": len(eligible),
            "value": round(100 * observed / target, 2) if observed is not None and target > 0 else None}


def evaluate_yield(db: Session, scheme_id: int, reports: list | None = None) -> dict:
    if reports is None:
        reports = list(db.scalars(select(CitizenScienceLog).where(CitizenScienceLog.scheme_id == scheme_id)))
    baselines = approved_baselines(db, scheme_id)
    comparisons = [compare(b, reports) for b in baselines]
    ready = [c for c in comparisons if c["value"] is not None]
    # Different crops/seasons must never be collapsed into a single percentage.
    value = ready[0]["value"] if len(ready) == 1 else None
    excluded = Counter(exclusion(r) for r in reports if exclusion(r))
    return {"value": value, "computable": value is not None, "formula": FORMULA,
            "comparisons": comparisons, "excluded": dict(excluded),
            "requirements": [
                {"item": "Approved, sourced crop/season/year target", "met": bool(baselines),
                 "note": f"{len(baselines)} approved target versions; legacy targets are not automatically approved"},
                {"item": "Verified measured harvests with harvested area and matching crop, season and year",
                 "met": bool(ready), "note": f"{sum(c['eligible_reports'] for c in ready)} eligible observations"},
                {"item": "One comparable group for the headline percentage", "met": len(ready) == 1,
                 "note": "Multiple groups are shown separately" if len(ready) > 1 else "No comparable group" if not ready else "Verified sample, not whole-scheme production or causal impact"},
            ]}
