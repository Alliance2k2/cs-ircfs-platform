"""PADAB / APEFA evaluation laboratory: the evidence per scheme, and a CSV export of it."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.csv_export import csv_download
from app.core.security import Principal, require_roles
from app.db.models import UserRole
from app.db.session import get_db
from app.services.audit import record
from app.services.evaluation import evaluate

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])
viewer = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
staff = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.get("")
def evaluation(days: int = Query(default=365, ge=30, le=1825), db: Session = Depends(get_db), _: Principal = viewer) -> dict:
    """Evidence per scheme for the five evaluation questions (aggregates only, no personal data)."""
    return evaluate(db, days)


@router.get("/export.csv")
def export_evaluation(days: int = Query(default=365, ge=30, le=1825), db: Session = Depends(get_db), principal: Principal = staff) -> StreamingResponse:
    """One row per comparable baseline group (or scheme if no approved target), with its source."""
    data = evaluate(db, days)
    header = ["scheme", "partner", "hectares_developed", "target_tons", "target_source", "target_state", "harvest_reports",
              "reported_tons", "expected_tons", "yield_achievement", "pest_alerts", "severe_pest_alerts", "assets_down",
              "assets_reported", "flagged_bottlenecks", "grievances", "open_grievances", "downstream_grievances",
              "reports", "located_percent", "verified_percent", "demo_percent", "months_with_reports", "period_days", "baseline_id", "crop", "season", "reference_year",
              "observed_yield_t_ha", "target_yield_t_ha", "harvested_area_ha", "eligible_reports", "source_document", "official_source"]
    rows = []
    for scheme in data["schemes"]:
        outcomes, bottlenecks, evidence = scheme["outcomes"], scheme["bottlenecks"], scheme["evidence"]
        rows.append([scheme["name"], scheme["implementing_partner"], scheme["hectares_developed"], scheme["documentation"]["target_tons"],
                     scheme["documentation"]["target_source"], scheme["documentation"]["state"], outcomes["harvest_reports"],
                     outcomes["reported_tons"], outcomes["expected_tons"], outcomes["yield_achievement"]["value"] if outcomes["yield_achievement"]["computable"] else "not computable (see requirements)", outcomes["pest_alerts"],
                     outcomes["severe_pest_alerts"], bottlenecks["assets_down"], bottlenecks["assets_reported"], ";".join(bottlenecks["flagged"]),
                     scheme["feedback"]["grievances"], scheme["feedback"]["open"], scheme["downstream"]["grievances"], evidence["reports"],
                     evidence["located_percent"], evidence["verified_percent"], evidence["demo_percent"], evidence["months_with_reports"], days])
    expanded = []
    for scheme, values in zip(data["schemes"], rows):
        comparisons = scheme["outcomes"]["yield_achievement"]["comparisons"]
        if not comparisons:
            expanded.append(values + [None] * 10)
        for group in comparisons:
            group_values = values.copy()
            group_values[9] = group["value"] if group["value"] is not None else "not computable (no eligible observations)"
            expanded.append(group_values + [group["baseline_id"], group["crop"], group["season"], group["reference_year"],
                            group["observed_tons_per_hectare"], group["target_tons_per_hectare"], group["harvested_area_hectares"],
                            group["eligible_reports"], group["document_reference"], group["source"]])
    rows = expanded
    record(db, principal, "evaluation.export", "evaluation", None, period_days=days)
    db.commit()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return csv_download(f"cs-ircfs-evaluation-{stamp}.csv", header, rows)
