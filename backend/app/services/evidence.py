"""Real current records count as evidence; demo presence is reported separately."""
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    ORIGIN_DEMO,
    ORIGIN_SIMULATOR,
    CitizenScienceLog,
    CommunityFeedback,
    InboundMessage,
    IrrigationClimateLog,
    IncidentCase,
    NutritionSurvey,
)

ORIGIN_MODELS = (CitizenScienceLog, IrrigationClimateLog, NutritionSurvey, CommunityFeedback, InboundMessage)


def counted(model):
    """Real current evidence only. Demo/simulator rows never enter official reporting."""
    if model is IncidentCase:
        return or_(
            and_(model.source_type == "crop", exists().where(CitizenScienceLog.id == model.source_id, counted(CitizenScienceLog))),
            and_(model.source_type == "infrastructure", exists().where(IrrigationClimateLog.id == model.source_id, counted(IrrigationClimateLog))),
        )
    conditions = [model.data_origin.in_(("field", "import"))]
    if hasattr(model, "superseded_by_id"):
        conditions.append(model.superseded_by_id.is_(None))
    return and_(*conditions)


def demo_mode(db: Session) -> bool:
    """True when any demonstration rows exist (scripts/seed_demo_data.py)."""
    return bool(db.scalar(select(or_(*(exists().where(model.data_origin == ORIGIN_DEMO) for model in ORIGIN_MODELS)))))
