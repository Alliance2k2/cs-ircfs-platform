"""Staff-only, stateless, read-only document assistant."""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator

from app.core.ratelimit import limiter
from app.core.security import Principal, require_roles
from app.db.models import UserRole
from app.services.assistant import respond

router = APIRouter(prefix="/api/v1/assistant", tags=["document assistant"])
staff = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1200)

    @field_validator("question")
    @classmethod
    def clean(cls, value):
        if len(value.strip()) < 3:
            raise ValueError("Enter a question")
        return value.strip()


@router.post("/ask")
@limiter.limit("10/minute")
async def ask(payload: Question, request: Request, _: Principal = staff):
    return await respond(payload.question)
