from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells, cell_filter
from app.core.security import Principal, require_roles
from app.db.models import IncentiveReward, NutritionSurvey, User, UserRole
from app.db.session import get_db
from app.schemas import NutritionSurveyCreate, NutritionSurveyRead
from app.services.advisory import nutrition_risk_score
from app.services.references import validate_report_references

router = APIRouter(prefix="/api/v1", tags=["food security and incentives"])
reporter = Depends(require_roles(UserRole.farmer, UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.administrator))
reader = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.post("/nutrition-surveys", response_model=NutritionSurveyRead, status_code=status.HTTP_201_CREATED)
def create_nutrition_survey(payload: NutritionSurveyCreate, db: Session = Depends(get_db), _: object = reporter) -> NutritionSurvey:
    """Household Nutrition Tracker entry (also collected through USSD option 6)."""
    validate_report_references(db, payload.reporter_id, None, payload.cell_id)
    survey = NutritionSurvey(**payload.model_dump(), stunting_risk_score=nutrition_risk_score(payload.meals_per_day, payload.ate_protein_or_vegetables, payload.food_sufficient))
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


@router.get("/nutrition-surveys", response_model=list[NutritionSurveyRead])
def list_nutrition_surveys(db: Session = Depends(get_db), principal: Principal = reader) -> list[NutritionSurvey]:
    cells = allowed_cells(db, principal)
    return list(db.scalars(select(NutritionSurvey).where(cell_filter(NutritionSurvey.cell_id, cells)).order_by(NutritionSurvey.id.desc())))


@router.get("/incentives")
def list_incentives(db: Session = Depends(get_db), principal: Principal = reader) -> list[dict]:
    """Airtime micro-bonuses earned by regular reporters."""
    area = allowed_cells(db, principal)
    people = None if area is None else set(db.scalars(select(User.id).where(User.cell_id.in_(area))))
    return [{"id": r.id, "user_id": r.user_id, "phone_number": r.phone_number, "amount_rwf": r.amount_rwf, "reason": r.reason,
             "status": r.status, "created_at": r.created_at}
            for r in db.scalars(select(IncentiveReward).order_by(IncentiveReward.id.desc())) if people is None or r.user_id in people]
