"""Which field records count as evidence, and whether the database holds demonstration data.

Simulator rows (training and testing on the on-screen phone) never count. Demonstration
rows count, so a demo database still shows figures, but the API reports ``demo_mode`` so
every screen can label them as demonstration data.
"""
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    ORIGIN_DEMO,
    ORIGIN_SIMULATOR,
    CitizenScienceLog,
    CommunityFeedback,
    InboundMessage,
    IrrigationClimateLog,
    NutritionSurvey,
)

ORIGIN_MODELS = (CitizenScienceLog, IrrigationClimateLog, NutritionSurvey, CommunityFeedback, InboundMessage)


def counted(model):
    """SQL condition: this row is evidence (not a simulator test)."""
    return model.data_origin != ORIGIN_SIMULATOR


def demo_mode(db: Session) -> bool:
    """True when any demonstration rows exist (scripts/seed_demo_data.py)."""
    return bool(db.scalar(select(or_(*(exists().where(model.data_origin == ORIGIN_DEMO) for model in ORIGIN_MODELS)))))
