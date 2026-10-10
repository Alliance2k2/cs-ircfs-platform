"""PADAB and APEFA evaluation: the evidence behind the five questions of the fellowship proposal.

1. Were expected outcomes achieved?            -> documentation, observed harvests, yield achievement
2. Which bottlenecks explain performance gaps? -> bottleneck counts against AfDB baselines, asset condition
3. What do beneficiaries say is unresolved?    -> grievances by category and status
4. What downstream or resettlement impacts?    -> grievances in that category
5. How reliable is the evidence?               -> evidence quality: completeness, verification, coverage

Nothing here is estimated or modelled. Yield achievement is only computed when observed
and target yields are comparable; otherwise the missing conditions are listed.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ORIGIN_DEMO, CitizenScienceLog, CommunityFeedback, IrrigationClimateLog, IrrigationScheme
from app.services.analytics import CLOSED, latest_asset_status, scheme_performance
from app.services.evidence import counted

QUESTIONS = [
    {"id": 1, "question": "Were the expected irrigation outcomes achieved?", "section": "outcomes"},
    {"id": 2, "question": "Which technical, environmental, institutional or social bottlenecks explain performance gaps?", "section": "bottlenecks"},
    {"id": 3, "question": "What unresolved issues does beneficiary feedback identify?", "section": "feedback"},
    {"id": 4, "question": "What impacts on affected or downstream communities have been recorded?", "section": "downstream"},
    {"id": 5, "question": "How reliable and complete is the supporting evidence?", "section": "evidence"},
]
DOWNSTREAM = ("resettlement", "downstream")


def pct(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def aware(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


def target_state(scheme: IrrigationScheme) -> str:
    if scheme.baseline_yield_target_tons is None or not scheme.baseline_source:
        return "missing"
    return "demo" if scheme.baseline_source.upper().startswith("DEMONSTRATION") else "documented"


def evaluate(db: Session, days: int = 365) -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    performance = {row["scheme_id"]: row for row in scheme_performance(db)}
    assets = latest_asset_status(db)
    schemes = []
    for scheme in db.scalars(select(IrrigationScheme).order_by(IrrigationScheme.name)):
        crop_reports = list(db.scalars(select(CitizenScienceLog).where(counted(CitizenScienceLog), CitizenScienceLog.scheme_id == scheme.id,
                                                                       CitizenScienceLog.created_at >= since)))
        water_reports = list(db.scalars(select(IrrigationClimateLog).where(counted(IrrigationClimateLog), IrrigationClimateLog.scheme_id == scheme.id,
                                                                           IrrigationClimateLog.created_at >= since)))
        grievances = list(db.scalars(select(CommunityFeedback).where(counted(CommunityFeedback), CommunityFeedback.scheme_id == scheme.id,
                                                                     CommunityFeedback.created_at >= since)))
        harvests = [report for report in crop_reports if not report.pest_or_disease]
        by_crop: dict[str, dict] = {}
        for report in harvests:
            item = by_crop.setdefault(report.crop_type, {"crop": report.crop_type, "reports": 0, "with_reported_tons": 0, "reported_tons": 0.0, "expected_tons": 0.0})
            item["reports"] += 1
            if report.reported_harvest_tons is not None:
                item["with_reported_tons"] += 1
                item["reported_tons"] = round(item["reported_tons"] + report.reported_harvest_tons, 2)
            item["expected_tons"] = round(item["expected_tons"] + (report.expected_harvest_tons or 0), 2)

        state = target_state(scheme)
        requirements = [
            {"item": "A yield target entered with its source document", "met": state == "documented",
             "note": {"documented": scheme.baseline_source, "demo": "Only a demonstration value is entered", "missing": "No documented target yet"}[state]},
            {"item": "The target stated per crop, per hectare and per season", "met": False,
             "note": "The platform stores one total target per scheme; crop, area and season are not recorded with it"},
            {"item": "Harvested area recorded on each harvest report", "met": False,
             "note": "USSD harvest reports record tons, not the area harvested, so yields per hectare cannot be derived"},
            {"item": "Verified harvest observations for the same season", "met": False,
             "note": f"{sum(1 for r in harvests if r.verification_status == 'verified')} of {len(harvests)} harvest reports are verified"},
        ]

        performance_row = performance.get(scheme.id, {})
        scheme_assets = [asset for asset in assets if asset["scheme_id"] == scheme.id]
        categories = Counter(item.category for item in grievances)
        downstream = [item for item in grievances if any(word in item.category.lower() for word in DOWNSTREAM)]
        all_reports = crop_reports + water_reports
        months = {aware(report.created_at).strftime("%Y-%m") for report in all_reports}
        located = sum(1 for report in all_reports if report.cell_id is not None or report.latitude is not None)
        verified = sum(1 for report in all_reports if report.verification_status == "verified")
        rejected = sum(1 for report in all_reports if report.verification_status == "rejected")
        demo = sum(1 for report in all_reports if report.data_origin == ORIGIN_DEMO)
        last = max((aware(report.created_at) for report in all_reports), default=None)

        schemes.append({
            "scheme_id": scheme.id, "name": scheme.name, "implementing_partner": scheme.implementing_partner,
            "hectares_developed": scheme.hectares_developed, "is_active": scheme.is_active,
            "documentation": {"target_tons": scheme.baseline_yield_target_tons, "target_source": scheme.baseline_source, "state": state},
            "outcomes": {
                "harvest_reports": len(harvests), "crops": sorted(by_crop.values(), key=lambda item: -item["reports"]),
                "reported_tons": round(sum(r.reported_harvest_tons or 0 for r in harvests), 2),
                "expected_tons": round(sum(r.expected_harvest_tons or 0 for r in harvests), 2),
                "pest_alerts": sum(1 for r in crop_reports if r.pest_or_disease), "severe_pest_alerts": sum(1 for r in crop_reports if (r.severity or 0) >= 4),
                "yield_achievement": {"value": None, "computable": False, "formula": "100 × comparable observed yield ÷ comparable target yield",
                                      "requirements": requirements},
            },
            "bottlenecks": {
                "window_days": performance_row.get("bottleneck_window_days"), "by_category": performance_row.get("bottlenecks", {}),
                "flagged": performance_row.get("flagged_bottlenecks", []), "above_baseline": performance_row.get("baseline_bottlenecks", []),
                "assets_reported": len(scheme_assets), "assets_down": sum(1 for asset in scheme_assets if asset["down"]),
                "fault_reports": sum(1 for r in water_reports if r.operational_status in ("faulty", "offline")),
            },
            "feedback": {
                "grievances": len(grievances), "open": sum(1 for item in grievances if item.status not in CLOSED),
                "resolved": sum(1 for item in grievances if item.status in CLOSED),
                "by_category": dict(categories.most_common()),
            },
            "downstream": {"grievances": len(downstream), "open": sum(1 for item in downstream if item.status not in CLOSED)},
            "evidence": {
                "reports": len(all_reports), "located_percent": pct(located, len(all_reports)), "verified_percent": pct(verified, len(all_reports)),
                "rejected": rejected, "demo_percent": pct(demo, len(all_reports)), "months_with_reports": len(months),
                "months_in_period": max(1, round(days / 30.4)), "last_report_at": last,
            },
        })
    return {"generated_at": now, "period_days": days, "questions": QUESTIONS, "schemes": schemes,
            "method": ("Counts of citizen and staff reports linked to each scheme in the period. Simulator tests are excluded; "
                       "demonstration rows are counted and labelled. No outcome is estimated, modelled or attributed causally: "
                       "a change over time shows association, not the effect of the investment.")}
