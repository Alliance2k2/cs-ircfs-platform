"""Authenticated delivery receipts and audited operator reconciliation."""
from datetime import datetime, timezone
import hmac
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes.channels import read_fields
from app.core.config import get_settings
from app.core.privacy import mask_phone
from app.core.security import Principal, require_roles
from app.db.models import DeliveryReceipt, UserRole
from app.db.session import get_db
from app.services.audit import record
from app.services.delivery_outbox import MODELS
from app.services.delivery_receipts import apply_receipts

router = APIRouter(prefix="/api/v1/delivery", tags=["delivery operations"])
admin = Depends(require_roles(UserRole.administrator))
STATUS = {
    "sms": {"success":"delivered", "delivered":"delivered", "failed":"failed", "rejected":"failed", "submitted":"sent", "buffered":"sent", "sent":"sent", "queued":"sent"},
    "airtime": {"success":"delivered", "failed":"failed", "sent":"sent"},
}


def verify_receipt_gateway(request: Request, token: str | None = Query(default=None)):
    # Unlike local inbound training callbacks, receipts are never public without a secret.
    settings = get_settings()
    expected = settings.gateway_callback_token.strip()
    if len(expected) < 24:
        raise HTTPException(403, "Delivery callbacks require a configured gateway secret")
    if not hmac.compare_digest((token or "").encode(), expected.encode()):
        raise HTTPException(403, "Unknown gateway")
    if settings.gateway_ips and (request.client is None or request.client.host not in settings.gateway_ips):
        raise HTTPException(403, "Unknown gateway")


async def receive(kind, request, db):
    fields = await read_fields(request)
    provider_id = fields.get("id" if kind == "sms" else "requestId", "").strip()
    raw = fields.get("status", "").strip().lower()
    if not provider_id or len(provider_id) > 120 or raw not in STATUS[kind]:
        raise HTTPException(422, "A known provider id/status pair is required")
    try:
        with db.begin_nested():
            db.add(DeliveryReceipt(kind=kind, provider_id=provider_id, provider_status=raw, normalized_status=STATUS[kind][raw]))
            db.flush()
    except IntegrityError:
        # Retries are idempotent, but still attempt correlation after an earlier send race.
        pass
    model = MODELS[kind]
    items = list(db.scalars(select(model).where(model.provider_id == provider_id).with_for_update()))
    if len(items) == 1:
        apply_receipts(db, kind, items[0])
    db.commit()
    return {"accepted": True, "matched": len(items) == 1}


@router.post("/sms", dependencies=[Depends(verify_receipt_gateway)])
async def sms_receipt(request: Request, db: Session = Depends(get_db)):
    return await receive("sms", request, db)


@router.post("/airtime", dependencies=[Depends(verify_receipt_gateway)])
async def airtime_receipt(request: Request, db: Session = Depends(get_db)):
    return await receive("airtime", request, db)


@router.get("/queue")
def queue(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db), _: Principal = admin):
    rows, totals = [], {}
    for kind, model in MODELS.items():
        totals[kind] = dict(db.execute(select(model.status, func.count()).group_by(model.status)).all())
        for item in db.scalars(select(model).order_by(model.id.desc()).limit(limit)):
            rows.append({"kind":kind, "id":item.id, "status":item.status, "phone_number":mask_phone(item.phone_number),
                "provider_id":item.provider_id, "delivery_attempts":item.delivery_attempts, "last_attempt_at":item.last_attempt_at,
                "created_at":item.created_at})
    return {"rows":rows, "totals":totals,
        "unmatched_receipts":db.scalar(select(func.count()).select_from(DeliveryReceipt).where(DeliveryReceipt.applied_at.is_(None))) or 0}


class Reconcile(BaseModel):
    action: Literal["accepted", "delivered", "failed", "requeue", "cancel"]
    reference: str = Field(min_length=5, max_length=255)
    provider_id: str | None = Field(default=None, min_length=1, max_length=120)
    confirmed_not_sent: bool = False

    @field_validator("reference")
    @classmethod
    def nonblank(cls, value):
        if len(value.strip()) < 5: raise ValueError("Give the provider evidence reference")
        return value.strip()


@router.post("/{kind}/{item_id}/reconcile")
def reconcile(kind: Literal["sms","airtime"], item_id: int, payload: Reconcile,
              db: Session = Depends(get_db), principal: Principal = admin):
    model = MODELS[kind]
    item = db.scalar(select(model).where(model.id == item_id).with_for_update())
    if item is None: raise HTTPException(404, "Delivery item not found")
    previous, previous_provider_id = item.status, item.provider_id
    if previous in ("dry_run", "delivered", "dispatching"):
        raise HTTPException(409, "This state cannot be manually changed")
    if payload.action == "requeue":
        if previous not in ("unknown","failed") or not payload.confirmed_not_sent:
            raise HTTPException(422, "Requeue requires provider confirmation that nothing was sent")
        if kind == "sms" and item.phone_number == "withheld":
            raise HTTPException(409, "Private routing has been erased; this reply cannot be replayed")
        item.status, item.provider_id = "queued", None
    elif payload.action == "cancel":
        if previous not in ("queued","unknown","failed"): raise HTTPException(409, "Accepted messages cannot be cancelled locally")
        item.status = "cancelled"
        if kind == "sms": item.private_recipient, item.private_recipient_expires_at = None, None
    else:
        if previous not in ("unknown","sent","failed"): raise HTTPException(409, "Reconcile an attempted message only")
        if payload.action in ("accepted", "delivered") and not (payload.provider_id or item.provider_id):
            raise HTTPException(422, "Provider acceptance/delivery needs the provider transaction id")
        item.provider_id = payload.provider_id or item.provider_id
        item.status = "sent" if payload.action == "accepted" else payload.action
        apply_receipts(db, kind, item)
    record(db, principal, "delivery.reconcile", "delivery", item.id, kind=kind, previous=previous,
        status=item.status, provider_reference=payload.reference, previous_provider_id=previous_provider_id,
        provider_id=item.provider_id, confirmed_not_sent=payload.confirmed_not_sent)
    db.commit()
    return {"status":item.status}
