"""USSD and SMS gateway callbacks (Africa's Talking format), the staff phone simulator,
and the channel activity feed.

Configure in the Africa's Talking dashboard (sandbox or live), with the shared secret
from GATEWAY_CALLBACK_TOKEN:
    USSD callback URL:   https://<host>/api/v1/ussd?token=<GATEWAY_CALLBACK_TOKEN>
    SMS callback URL:    https://<host>/api/v1/sms/inbound?token=<GATEWAY_CALLBACK_TOKEN>

Africa's Talking does not sign its callbacks, so the secret in the URL (and optionally
GATEWAY_ALLOWED_IPS) is what tells a real gateway request from a forged one. The
simulator has its own signed-in endpoints and never reaches a telecom provider.
"""
import hmac
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select, true, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.privacy import WITHHELD, mask_phone, sees_personal_data
from app.core.scope import allowed_cells, cell_filter
from app.core.security import Principal, require_roles
from app.db.models import (
    ORIGIN_FIELD,
    ORIGIN_SIMULATOR,
    AdvisoryMessage,
    CitizenScienceLog,
    CommunityFeedback,
    FieldUser,
    IncentiveReward,
    InboundMessage,
    IrrigationClimateLog,
    NutritionSurvey,
    UserRole,
)
from app.db.session import get_db
from app.services import sms_keywords, ussd
from app.services.reporting import find_or_register_user
from app.services.sms import deliver, is_valid_phone, normalise_phone, simulation

router = APIRouter(prefix="/api/v1", tags=["field channels"])
reader = Depends(require_roles(UserRole.citizen_science_monitor, UserRole.cooperative_leader, UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
# Training and testing on the on-screen phone: any signed-in staff role.
simulator_user = reader

GRIEVANCE = "community_feedback"
RECORD_MODELS = {"crop_report": CitizenScienceLog, "irrigation_report": IrrigationClimateLog,
                 "nutrition_survey": NutritionSurvey, GRIEVANCE: CommunityFeedback}
# Per caller, across all workers (the database is shared): a USSD session is a few
# keypresses, so this only stops a runaway client, never a real farmer.
PHONE_LIMIT_PER_MINUTE = 30


async def read_fields(request: Request) -> dict[str, str]:
    """Accept Africa's Talking form posts and JSON from the dashboard simulator."""
    body = (await request.body()).decode("utf-8", errors="replace")
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            data = json.loads(body or "{}")
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=422, detail="Invalid JSON body") from error
        if not isinstance(data, dict):
            raise HTTPException(status_code=422, detail="Expected a JSON object")
        return {key: str(value) for key, value in data.items() if value is not None}
    return {key: values[-1] for key, values in parse_qs(body, keep_blank_values=True).items()}


def caller(fields: dict[str, str], key: str) -> str:
    phone = normalise_phone(fields.get(key, ""))
    if not is_valid_phone(phone):
        raise HTTPException(status_code=422, detail="A valid phone number is required")
    return phone


def verify_gateway(request: Request, token: str | None = Query(default=None)) -> None:
    """Accept only requests carrying the shared callback secret (and from an allowed address).

    Without GATEWAY_CALLBACK_TOKEN the callbacks stay open, which the production guard
    refuses; that keeps the Africa's Talking sandbox and local tests simple.
    """
    settings = get_settings()
    expected = settings.gateway_callback_token.strip()
    if expected and not hmac.compare_digest((token or "").encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="Unknown gateway")
    allowed = settings.gateway_ips
    if allowed and (request.client is None or request.client.host not in allowed):
        raise HTTPException(status_code=403, detail="Unknown gateway")


def throttle(db: Session, phone: str) -> None:
    since = datetime.now(timezone.utc) - timedelta(minutes=1)
    recent = db.scalar(select(func.count()).select_from(InboundMessage)
                       .where(InboundMessage.phone_number == phone, InboundMessage.created_at >= since)) or 0
    if recent >= PHONE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")


def tag_origin(db: Session, record_type: str | None, record_id: int | None, origin: str) -> None:
    """Mark the record a handler created (simulator rows are left out of the evidence)."""
    model = RECORD_MODELS.get(record_type or "")
    if model is not None and record_id is not None and origin != ORIGIN_FIELD:
        record = db.get(model, record_id)
        if record is not None:
            record.data_origin = origin


def run_ussd(db: Session, fields: dict[str, str], origin: str) -> tuple[ussd.UssdResult | None, InboundMessage | None]:
    """One USSD keypress. Returns (result, None), or (None, earlier) for a gateway retry."""
    phone = caller(fields, "phoneNumber")
    text = fields.get("text", "")
    session_id = fields.get("sessionId")
    # A gateway retry repeats the same sessionId and text. Replay the stored reply instead
    # of recording the report a second time.
    if session_id:
        earlier = db.scalar(select(InboundMessage).where(
            InboundMessage.channel == "ussd", InboundMessage.session_id == session_id, InboundMessage.text == (text or "(dial)")).limit(1))
        if earlier is not None:
            return None, earlier
    throttle(db, phone)
    user = find_or_register_user(db, phone)
    result = ussd.handle(db, user, text)
    tag_origin(db, result.record_type, result.record_id, origin)
    stored_phone = phone
    if result.record_type == GRIEVANCE:
        # Grievances are anonymous: drop the phone from every step of this session, so the
        # log cannot tie a number to the grievance (or its FB reference in the reply).
        stored_phone = WITHHELD
        if session_id:
            db.execute(update(InboundMessage).where(InboundMessage.channel == "ussd", InboundMessage.session_id == session_id)
                       .values(phone_number=WITHHELD))
    db.add(InboundMessage(phone_number=stored_phone, channel="ussd", session_id=session_id, text=text or "(dial)", reply=result.response,
                          record_type=result.record_type, record_id=None if result.record_type == GRIEVANCE else result.record_id,
                          data_origin=origin))
    db.commit()
    return result, None


def run_sms(db: Session, fields: dict[str, str], origin: str) -> dict:
    phone = caller(fields, "from")
    text = fields.get("text", "")
    message_id = fields.get("id") or None
    # Africa's Talking retries a callback it thinks failed. The same message ID must not
    # create a second report or a second reply.
    if message_id:
        earlier = db.scalar(select(InboundMessage).where(InboundMessage.channel == "sms", InboundMessage.session_id == message_id).limit(1))
        if earlier is not None:
            return {"reply": earlier.reply, "reply_status": "duplicate", "record_type": earlier.record_type, "record_id": earlier.record_id}
    throttle(db, phone)
    user = find_or_register_user(db, phone)
    result = sms_keywords.handle(db, user, text)
    tag_origin(db, result.record_type, result.record_id, origin)
    anonymous = result.record_type == GRIEVANCE
    reply = deliver(db, phone, result.reply, purpose="auto_reply", cell_id=user.cell_id, anonymous=anonymous)
    db.add(InboundMessage(phone_number=WITHHELD if anonymous else phone, channel="sms", session_id=message_id, text=text, reply=result.reply,
                          record_type=result.record_type, record_id=None if anonymous else result.record_id, data_origin=origin))
    db.commit()
    return {"reply": result.reply, "reply_status": reply.status, "record_type": result.record_type, "record_id": result.record_id}


@router.post("/ussd", dependencies=[Depends(verify_gateway)])
async def ussd_callback(request: Request, db: Session = Depends(get_db)):
    """One USSD keypress from the gateway. Returns plain text 'CON …' or 'END …'."""
    fields = await read_fields(request)
    result, earlier = run_ussd(db, fields, ORIGIN_FIELD)
    return PlainTextResponse((earlier.reply or "") if earlier is not None else result.response)


@router.post("/sms/inbound", dependencies=[Depends(verify_gateway)])
async def sms_callback(request: Request, db: Session = Depends(get_db)):
    """An SMS sent by a citizen to the keyword short code. The reply is sent back by SMS."""
    return run_sms(db, await read_fields(request), ORIGIN_FIELD)


@router.post("/simulator/ussd")
async def simulator_ussd(request: Request, db: Session = Depends(get_db), _: Principal = simulator_user) -> dict:
    """The on-screen phone: same menu as *801#, with an English translation of each screen.

    Records are marked as simulator data and nothing is sent to a telecom provider.
    """
    fields = await read_fields(request)
    with simulation():
        result, earlier = run_ussd(db, fields, ORIGIN_SIMULATOR)
    service_code = get_settings().ussd_service_code
    if earlier is not None:
        return {"response": earlier.reply, "english": "", "record_type": earlier.record_type, "record_id": earlier.record_id,
                "service_code": service_code, "reply_status": "duplicate"}
    return {"response": result.response, "english": result.english, "record_type": result.record_type, "record_id": result.record_id,
            "service_code": service_code}


@router.post("/simulator/sms")
async def simulator_sms(request: Request, db: Session = Depends(get_db), _: Principal = simulator_user) -> dict:
    """The on-screen phone's SMS to 8448. The reply is recorded as dry-run, never sent."""
    fields = await read_fields(request)
    with simulation():
        return run_sms(db, fields, ORIGIN_SIMULATOR)


@router.get("/channels/activity")
def channel_activity(limit: int = Query(default=30, ge=1, le=200), db: Session = Depends(get_db), principal: Principal = reader) -> dict:
    """Latest inbound USSD/SMS, outbound SMS, and airtime rewards, for the live feed.

    Monitors and cooperative leaders see masked numbers and no message text.
    """
    area = allowed_cells(db, principal)
    full = sees_personal_data(principal)
    phone = (lambda value: value) if full else mask_phone
    words = (lambda value: value) if full else (lambda _value: None)
    # Inbound messages carry no cell: an area-limited person sees messages from phones registered in their area.
    phones = select(FieldUser.phone_number).where(FieldUser.cell_id.in_(area)) if area is not None else None
    inbound = db.scalars(select(InboundMessage).where(InboundMessage.phone_number.in_(phones) if phones is not None else true())
                         .order_by(InboundMessage.id.desc()).limit(limit))
    outbound = db.scalars(select(AdvisoryMessage).where(cell_filter(AdvisoryMessage.cell_id, area)).order_by(AdvisoryMessage.id.desc()).limit(limit))
    rewards = db.scalars(select(IncentiveReward).where(IncentiveReward.phone_number.in_(phones) if phones is not None else true())
                         .order_by(IncentiveReward.id.desc()).limit(limit))
    return {
        "inbound": [{"id": m.id, "phone_number": phone(m.phone_number), "channel": m.channel, "text": words(m.text), "reply": words(m.reply),
                     "record_type": m.record_type, "record_id": m.record_id, "data_origin": m.data_origin, "created_at": m.created_at} for m in inbound],
        "outbound": [{"id": m.id, "phone_number": phone(m.phone_number), "message": words(m.message), "status": m.status, "purpose": m.purpose,
                      "cell_id": m.cell_id, "created_at": m.created_at} for m in outbound],
        "rewards": [{"id": r.id, "phone_number": phone(r.phone_number), "amount_rwf": r.amount_rwf, "reason": r.reason, "status": r.status,
                     "created_at": r.created_at} for r in rewards],
        "personal_data": full,
        "service_code": get_settings().ussd_service_code,
        "sms_shortcode": get_settings().sms_shortcode,
    }
