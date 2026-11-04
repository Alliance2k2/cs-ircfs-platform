"""Post-commit delivery with atomic claims; uncertain outcomes are never auto-replayed.

Provider acceptance is recorded as `sent`, never as confirmed handset delivery.
Ordinary SMS and airtime share a safe claim protocol. Optional private reply routes
are short-lived, encrypted, and erased before provider access. They require policy opt-in.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, select, update

from app.core.config import get_settings
from app.db.models import AdvisoryMessage, FieldUser, IncentiveReward
from app.services.sms import is_valid_phone, live, send_airtime, send_sms

MODELS = {"sms": AdvisoryMessage, "airtime": IncentiveReward}


def dispatch_one(factory, kind):
    model = MODELS[kind]
    settings = get_settings()
    provider = settings.sms_provider if kind == "sms" else settings.airtime_provider
    if not live(provider):
        return "disabled"
    with factory() as db:
        candidate = db.scalar(select(model.id).where(model.status == "queued").order_by(model.id).limit(1))
        if candidate is None:
            return "empty"
        claim = db.execute(update(model).where(model.id == candidate, model.status == "queued").values(
            status="dispatching", delivery_attempts=model.delivery_attempts + 1,
            last_attempt_at=datetime.now(timezone.utc)))
        if claim.rowcount != 1:
            db.rollback()
            return "contended"
        db.commit()  # claim is durable before the network operation
        item = db.get(model, candidate)
        target = item.phone_number
        if kind == "sms" and item.private_recipient:
            from app.services.private_replies import open_route
            target = open_route(item)
            item.private_recipient, item.private_recipient_expires_at = None, None
            db.commit()  # erase the temporary link before any provider call
        person = db.scalar(select(FieldUser).where(FieldUser.phone_number == target))
        invalid = not is_valid_phone(target or "") or (person is not None and person.data_origin == "simulator")
        broadcast = kind == "sms" and item.purpose in ("irrigation_schedule", "close_loop", "local_tip")
        created = item.created_at.replace(tzinfo=timezone.utc) if item.created_at.tzinfo is None else item.created_at
        stale = datetime.now(timezone.utc) - created > timedelta(hours=settings.delivery_max_age_hours)
        if invalid or stale or (broadcast and (person is None or not person.is_active or person.opted_out_at is not None)):
            item.status = "cancelled"
            db.commit()
            return "cancelled"
        try:
            result = send_sms(target, item.message) if kind == "sms" else send_airtime(target, item.amount_rwf)
        except Exception:
            # A transport/client failure may occur after provider acceptance.
            result = {"status": "unknown"}
        outcome = result.get("status", "unknown")
        item.status = outcome if outcome in ("sent", "dry_run") else "unknown"
        item.provider_id = result.get("provider_id")
        from app.services.delivery_receipts import apply_receipts
        apply_receipts(db, kind, item)
        db.commit()
        return item.status


def mark_stale_claims_unknown(factory, minutes=5):
    """Operator recovery after a crash: flag for reconciliation, never resend blindly."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    with factory() as db:
        total = 0
        for model in MODELS.values():
            result = db.execute(update(model).where(model.status == "dispatching", model.last_attempt_at < cutoff)
                                .values(status="unknown"))
            total += result.rowcount
        db.commit()
        return total


def erase_expired_routes(factory):
    with factory() as db:
        now = datetime.now(timezone.utc)
        result = db.execute(update(AdvisoryMessage).where(AdvisoryMessage.private_recipient_expires_at <= now,
            AdvisoryMessage.private_recipient.is_not(None)).values(private_recipient=None,
            private_recipient_expires_at=None, status=case((AdvisoryMessage.status == "queued", "cancelled"), else_=AdvisoryMessage.status)))
        db.commit()
        return result.rowcount
