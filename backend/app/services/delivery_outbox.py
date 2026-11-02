"""Post-commit delivery with atomic claims; uncertain outcomes are never auto-replayed.

Provider acceptance is recorded as `sent`, never as confirmed handset delivery.
Ordinary SMS and airtime share the same safe claim protocol. Anonymous replies are
not queued because retaining their recipient would undo grievance anonymity.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

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
        person = db.scalar(select(FieldUser).where(FieldUser.phone_number == item.phone_number))
        invalid = not is_valid_phone(item.phone_number) or (person is not None and person.data_origin == "simulator")
        broadcast = kind == "sms" and item.purpose in ("irrigation_schedule", "close_loop", "local_tip")
        if invalid or (broadcast and (person is None or not person.is_active or person.opted_out_at is not None)):
            item.status = "cancelled"
            db.commit()
            return "cancelled"
        try:
            result = send_sms(item.phone_number, item.message) if kind == "sms" else send_airtime(item.phone_number, item.amount_rwf)
        except Exception:
            # A transport/client failure may occur after provider acceptance.
            result = {"status": "unknown"}
        outcome = result.get("status", "unknown")
        item.status = outcome if outcome in ("sent", "dry_run") else "unknown"
        item.provider_id = result.get("provider_id")
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
