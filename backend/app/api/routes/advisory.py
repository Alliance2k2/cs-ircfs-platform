from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.security import require_roles
from app.db.models import AdvisoryMessage, UserRole
from app.db.session import get_db
from app.services.sms import send_sms

router = APIRouter(prefix="/api/v1/advisory", tags=["farmer advisory"])
admin = Depends(require_roles(UserRole.administrator, UserRole.district_planner))

@router.post("/sms")
def send_advisory_sms(phone_number: str, message: str, db: Session = Depends(get_db), _: object = admin):
    result = send_sms(phone_number, message)
    status = result.get("status", "sent") if isinstance(result, dict) else "sent"
    record = AdvisoryMessage(phone_number=phone_number, message=message, status=status)
    db.add(record); db.commit(); db.refresh(record)
    return {"id": record.id, "status": status, "provider_response": result}
