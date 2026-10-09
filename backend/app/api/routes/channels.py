"""USSD and SMS gateway callbacks (Africa's Talking format) and the channel activity feed.

Configure in the Africa's Talking dashboard (sandbox or live):
    USSD callback URL:   https://<host>/api/v1/ussd
    SMS callback URL:    https://<host>/api/v1/sms/inbound

The callbacks are public because the telecom aggregator calls them directly, so they
carry a per-IP rate limit.
"""
import json
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import true, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.ratelimit import limiter
from app.core.scope import allowed_cells, cell_filter
from app.core.security import Principal, require_roles
from app.db.models import AdvisoryMessage, FieldUser, IncentiveReward, InboundMessage, UserRole
from app.db.session import get_db
from app.services import sms_keywords, ussd
from app.services.reporting import find_or_register_user
from app.services.sms import deliver, is_valid_phone, normalise_phone

router = APIRouter(prefix="/api/v1", tags=["field channels"])
reader = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))


async def read_fields(request: Request) -> dict[str, str]:
    """Accept Africa's Talking form posts and JSON from the dashboard simulator."""
    body = (await request.body()).decode("utf-8", errors="replace")
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            data = json.loads(body or "{}")
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=422, detail="Invalid JSON body") from error
        return {key: str(value) for key, value in data.items() if value is not None}
    return {key: values[-1] for key, values in parse_qs(body, keep_blank_values=True).items()}


def caller(fields: dict[str, str], key: str) -> str:
    phone = normalise_phone(fields.get(key, ""))
    if not is_valid_phone(phone):
        raise HTTPException(status_code=422, detail="A valid phone number is required")
    return phone


@router.post("/ussd")
@limiter.limit("30/minute")
async def ussd_callback(request: Request, explain: bool = Query(default=False), db: Session = Depends(get_db)):
    """One USSD keypress. Returns plain text 'CON …' or 'END …' as Africa's Talking expects.

    With ``?explain=true`` (used by the dashboard simulator) the reply is JSON that also
    carries an English translation and the record that was created.
    """
    fields = await read_fields(request)
    phone = caller(fields, "phoneNumber")
    text = fields.get("text", "")
    session_id = fields.get("sessionId")
    # A gateway retry repeats the same sessionId and text. Replay the stored reply instead
    # of recording the report a second time.
    if session_id:
        earlier = db.scalar(select(InboundMessage).where(
            InboundMessage.channel == "ussd", InboundMessage.session_id == session_id, InboundMessage.text == (text or "(dial)")).limit(1))
        if earlier is not None:
            if explain:
                return {"response": earlier.reply, "english": "", "record_type": earlier.record_type, "record_id": earlier.record_id,
                        "service_code": get_settings().ussd_service_code, "reply_status": "duplicate"}
            return PlainTextResponse(earlier.reply or "")
    user = find_or_register_user(db, phone)
    result = ussd.handle(db, user, text)
    db.add(InboundMessage(phone_number=phone, channel="ussd", session_id=session_id, text=text or "(dial)",
                          reply=result.response, record_type=result.record_type, record_id=result.record_id))
    db.commit()
    if explain:
        return {"response": result.response, "english": result.english, "record_type": result.record_type, "record_id": result.record_id,
                "service_code": get_settings().ussd_service_code}
    return PlainTextResponse(result.response)


@router.post("/sms/inbound")
@limiter.limit("30/minute")
async def sms_callback(request: Request, db: Session = Depends(get_db)):
    """An SMS sent by a citizen to the keyword short code. The reply is sent back by SMS."""
    fields = await read_fields(request)
    phone = caller(fields, "from")
    text = fields.get("text", "")
    message_id = fields.get("id") or None
    # Africa's Talking retries a callback it thinks failed. The same message ID must not
    # create a second report or a second reply.
    if message_id:
        earlier = db.scalar(select(InboundMessage).where(InboundMessage.channel == "sms", InboundMessage.session_id == message_id).limit(1))
        if earlier is not None:
            return {"reply": earlier.reply, "reply_status": "duplicate", "record_type": earlier.record_type, "record_id": earlier.record_id}
    user = find_or_register_user(db, phone)
    result = sms_keywords.handle(db, user, text)
    reply = deliver(db, phone, result.reply, purpose="auto_reply", cell_id=user.cell_id)
    db.add(InboundMessage(phone_number=phone, channel="sms", session_id=fields.get("id"), text=text, reply=result.reply,
                          record_type=result.record_type, record_id=result.record_id))
    db.commit()
    return {"reply": result.reply, "reply_status": reply.status, "record_type": result.record_type, "record_id": result.record_id}


@router.get("/channels/activity")
def channel_activity(limit: int = Query(default=30, ge=1, le=200), db: Session = Depends(get_db), principal: Principal = reader) -> dict:
    """Latest inbound USSD/SMS, outbound SMS, and airtime rewards, for the live feed."""
    area = allowed_cells(db, principal)
    # Inbound messages carry no cell: an area-limited person sees messages from phones registered in their area.
    phones = select(FieldUser.phone_number).where(FieldUser.cell_id.in_(area)) if area is not None else None
    inbound = db.scalars(select(InboundMessage).where(InboundMessage.phone_number.in_(phones) if phones is not None else true())
                         .order_by(InboundMessage.id.desc()).limit(limit))
    outbound = db.scalars(select(AdvisoryMessage).where(cell_filter(AdvisoryMessage.cell_id, area)).order_by(AdvisoryMessage.id.desc()).limit(limit))
    rewards = db.scalars(select(IncentiveReward).where(IncentiveReward.phone_number.in_(phones) if phones is not None else true())
                         .order_by(IncentiveReward.id.desc()).limit(limit))
    return {
        "inbound": [{"id": m.id, "phone_number": m.phone_number, "channel": m.channel, "text": m.text, "reply": m.reply,
                     "record_type": m.record_type, "record_id": m.record_id, "created_at": m.created_at} for m in inbound],
        "outbound": [{"id": m.id, "phone_number": m.phone_number, "message": m.message, "status": m.status, "purpose": m.purpose,
                      "cell_id": m.cell_id, "created_at": m.created_at} for m in outbound],
        "rewards": [{"id": r.id, "phone_number": r.phone_number, "amount_rwf": r.amount_rwf, "reason": r.reason, "status": r.status,
                     "created_at": r.created_at} for r in rewards],
        "service_code": get_settings().ussd_service_code,
        "sms_shortcode": get_settings().sms_shortcode,
    }
