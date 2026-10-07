from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import AdvisoryMessage, Cell, User, UserRole
from app.db.session import get_db
from app.schemas import AdvisorySmsCreate, ScheduleBroadcast
from app.services.advisory import sector_schedule
from app.services.sms import deliver, is_valid_phone, normalise_phone

router = APIRouter(prefix="/api/v1/advisory", tags=["farmer advisory"])
admin = Depends(require_roles(UserRole.administrator, UserRole.district_planner))
planner = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
viewer = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.post("/sms")
def send_advisory_sms(payload: AdvisorySmsCreate, db: Session = Depends(get_db), _: object = admin):
    phone = normalise_phone(payload.phone_number)
    if not is_valid_phone(phone):
        raise HTTPException(status_code=422, detail="Enter a valid phone number, for example +250788123456")
    record = deliver(db, phone, payload.message.strip(), purpose="advisory")
    db.commit(); db.refresh(record)
    return {"id": record.id, "status": record.status, "provider_id": record.provider_id}


@router.get("/messages")
def list_messages(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db), _: object = planner) -> list[dict]:
    return [{"id": m.id, "phone_number": m.phone_number, "message": m.message, "status": m.status, "purpose": m.purpose or "advisory",
             "cell_id": m.cell_id, "created_at": m.created_at}
            for m in db.scalars(select(AdvisoryMessage).order_by(AdvisoryMessage.id.desc()).limit(limit))]


@router.get("/irrigation-schedule")
def irrigation_schedule(db: Session = Depends(get_db), _: object = viewer) -> list[dict]:
    """Irrigation Scheduling Assistant: 7-day rainfall per sector and the advice it triggers."""
    return sector_schedule(db)


@router.post("/irrigation-schedule/send")
def send_irrigation_schedule(payload: ScheduleBroadcast, db: Session = Depends(get_db), _: object = admin) -> dict:
    """SMS each sector's advice to its cooperative leaders and Citizen Science Monitors."""
    schedule = [row for row in sector_schedule(db) if row["level"] != "no_data" and (not payload.sector_ids or row["sector_id"] in payload.sector_ids)]
    sent = []
    for row in schedule:
        recipients = db.execute(
            select(User.phone_number, User.cell_id).join(Cell, Cell.id == User.cell_id)
            .where(Cell.sector_id == row["sector_id"], User.is_active.is_(True),
                   User.role.in_([UserRole.cooperative_leader, UserRole.citizen_science_monitor, UserRole.farmer]))
        ).all()
        if not payload.preview:
            for phone, cell_id in recipients:
                deliver(db, phone, row["message_rw"], purpose="irrigation_schedule", cell_id=cell_id)
        sent.append({"sector": row["sector"], "level": row["level"], "recipients": len(recipients), "message_rw": row["message_rw"], "message_en": row["message_en"]})
    if not payload.preview:
        db.commit()
    return {"preview": payload.preview, "sectors": sent, "total_recipients": sum(item["recipients"] for item in sent)}
