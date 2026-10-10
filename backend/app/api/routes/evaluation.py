"""PADAB / APEFA evaluation laboratory: the evidence per scheme, and a CSV export of it."""
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

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
    """One row per scheme with every headline indicator and its source, for the evaluation report."""
    data = evaluate(db, days)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["scheme", "partner", "hectares_developed", "target_tons", "target_source", "target_state", "harvest_reports",
                     "reported_tons", "expected_tons", "yield_achievement", "pest_alerts", "severe_pest_alerts", "assets_down",
                     "assets_reported", "flagged_bottlenecks", "grievances", "open_grievances", "downstream_grievances",
                     "reports", "located_percent", "verified_percent", "demo_percent", "months_with_reports", "period_days"])
    for scheme in data["schemes"]:
        outcomes, bottlenecks, evidence = scheme["outcomes"], scheme["bottlenecks"], scheme["evidence"]
        writer.writerow([scheme["name"], scheme["implementing_partner"], scheme["hectares_developed"], scheme["documentation"]["target_tons"],
                         scheme["documentation"]["target_source"], scheme["documentation"]["state"], outcomes["harvest_reports"],
                         outcomes["reported_tons"], outcomes["expected_tons"], "not computable (see requirements)", outcomes["pest_alerts"],
                         outcomes["severe_pest_alerts"], bottlenecks["assets_down"], bottlenecks["assets_reported"], ";".join(bottlenecks["flagged"]),
                         scheme["feedback"]["grievances"], scheme["feedback"]["open"], scheme["downstream"]["grievances"], evidence["reports"],
                         evidence["located_percent"], evidence["verified_percent"], evidence["demo_percent"], evidence["months_with_reports"], days])
    record(db, principal, "evaluation.export", "evaluation", None, period_days=days)
    db.commit()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="cs-ircfs-evaluation-{stamp}.csv"'})
