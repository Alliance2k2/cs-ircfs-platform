"""Outbound advisory SMS, irrigation scheduling, and airtime incentives."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.scope import allowed_cells, cell_filter
from app.core.security import Principal, require_roles
from app.db.models import AdvisoryMessage, FieldUser, IncentiveReward, UserRole
from app.db.session import get_db
from app.schemas import AdvisorySmsCreate, ScheduleBroadcast
from app.services.audit import record
from app.services.advisory import broadcast_advice, sector_schedule, weekly_advice_status
from app.services.sms import deliver, is_valid_phone, normalise_phone

router = APIRouter(prefix="/api/v1/advisory", tags=["farmer advisory"])
admin = Depends(require_roles(UserRole.administrator, UserRole.district_planner))
planner = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
viewer = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
reader = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


@router.post("/sms")
def send_advisory_sms(payload: AdvisorySmsCreate, db: Session = Depends(get_db), _: object = admin):
    phone = normalise_phone(payload.phone_number)
    if not is_valid_phone(phone):
        raise HTTPException(status_code=422, detail="Enter a valid phone number, for example +250788123456")
    record = deliver(db, phone, payload.message.strip(), purpose="advisory")
    db.commit()
    db.refresh(record)
    return {"id": record.id, "status": record.status, "provider_id": record.provider_id}


@router.get("/messages")
def list_messages(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db), principal: Principal = planner) -> list[dict]:
    cells = allowed_cells(db, principal)
    return [{"id": m.id, "phone_number": m.phone_number, "message": m.message, "status": m.status, "purpose": m.purpose or "advisory",
             "cell_id": m.cell_id, "created_at": m.created_at}
            for m in db.scalars(select(AdvisoryMessage).where(cell_filter(AdvisoryMessage.cell_id, cells)).order_by(AdvisoryMessage.id.desc()).limit(limit))]


@router.get("/incentives")
def list_incentives(db: Session = Depends(get_db), principal: Principal = reader) -> list[dict]:
    """Airtime micro-bonuses earned by regular reporters."""
    area = allowed_cells(db, principal)
    people = None if area is None else set(db.scalars(select(FieldUser.id).where(FieldUser.cell_id.in_(area))))
    return [{"id": r.id, "field_user_id": r.field_user_id, "phone_number": r.phone_number, "amount_rwf": r.amount_rwf, "reason": r.reason,
             "status": r.status, "created_at": r.created_at}
            for r in db.scalars(select(IncentiveReward).order_by(IncentiveReward.id.desc())) if people is None or r.field_user_id in people]


@router.get("/irrigation-schedule")
def irrigation_schedule(db: Session = Depends(get_db), _: object = viewer) -> list[dict]:
    """Irrigation Scheduling Assistant: 7-day rainfall per sector and the advice it triggers."""
    return sector_schedule(db)


@router.get("/weekly-advice")
def weekly_advice(db: Session = Depends(get_db), _: object = viewer) -> dict:
    """Last automatic advice send and the next scheduled run (WP2), for advice.html."""
    return weekly_advice_status(db)


@router.post("/irrigation-schedule/send")
def send_irrigation_schedule(payload: ScheduleBroadcast, db: Session = Depends(get_db), principal: Principal = admin) -> dict:
    """SMS each sector's advice to its cooperative leaders and Citizen Science Monitors (only the sender's own sectors)."""
    schedule = [row for row in sector_schedule(db) if row["level"] != "no_data" and (not payload.sector_ids or row["sector_id"] in payload.sector_ids)
                and (principal.sector_ids is None or row["sector_id"] in principal.sector_ids)]
    sent = broadcast_advice(db, schedule, preview=payload.preview)
    if not payload.preview:
        record(db, principal, "advice.send", "advice", None, sectors=[item["sector"] for item in sent],
               recipients=sum(item["recipients"] for item in sent))
        db.commit()
    return {"preview": payload.preview, "sectors": sent, "total_recipients": sum(item["recipients"] for item in sent)}
