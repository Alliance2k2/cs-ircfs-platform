"""Read-only evidence readiness: counts and missingness, never invented ML readiness."""
from sqlalchemy import func, select
from app.db.models import (CitizenScienceLog, SchemeBaseline, RainfallReference, SchemeAsset, FieldUser,
    IrrigationScheme, PlatformAccount)
from app.services.evidence import counted


def assess(db):
    reports=list(db.scalars(select(CitizenScienceLog).where(counted(CitizenScienceLog))))
    verified=[r for r in reports if r.verification_status=="verified"]
    from app.services.yield_evaluation import exclusion
    from collections import Counter
    measured=[r for r in reports if exclusion(r) is None]
    reasons=Counter(exclusion(r) for r in reports if exclusion(r))
    groups={}
    for report in measured:
        key=(report.scheme_id,report.crop_type,report.season,report.reference_year)
        groups[key]=groups.get(key,0)+1
    approved = db.scalar(select(func.count()).select_from(SchemeBaseline).where(SchemeBaseline.verification_status=="verified",
        SchemeBaseline.approved_at.is_not(None),counted(SchemeBaseline))) or 0
    references=db.scalar(select(func.count()).select_from(RainfallReference).where(RainfallReference.approved_at.is_not(None),
        RainfallReference.data_origin.in_(["field","import"]))) or 0
    return {"field_crop_reports":len(reports),"verified_crop_reports":len(verified),"measured_yield_reports":len(measured),
        "exclusion_reasons":dict(reasons),"approved_baseline_versions":approved,"approved_rainfall_references":references,
        "inventory_without_confirmed_cell":db.scalar(select(func.count()).select_from(SchemeAsset).where(SchemeAsset.cell_id.is_(None))) or 0,
        "inactive_or_uncovered_schemes":sum(1 for s in db.scalars(select(IrrigationScheme)) if not s.is_active or not _covered(db,s)),
        "active_administrators":db.scalar(select(func.count()).select_from(PlatformAccount).where(PlatformAccount.status=="active",PlatformAccount.role=="administrator")) or 0,
        "measurement_groups":[{"scheme_id":k[0],"crop":k[1],"season":k[2],"year":k[3],"reports":v} for k,v in groups.items()],
        "ml_training_authorized":False,"causal_impact_established":False,
        "limitations":["Counts are not a representative sampling design or proof of causal impact.",
            "ML needs approved targets, adequate independent seasons/holdouts, missingness review, consent and a documented validation protocol.",
            "Official document entry, native-language review, real-phone acceptance and district privacy sign-off require external evidence."]}


def _covered(db,scheme):
    from app.services.scheme_coverage import sector_ids_for_scheme
    return bool(sector_ids_for_scheme(db,scheme))
