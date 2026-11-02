from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import Settings
from app.db.models import AdvisoryMessage, FieldUser, IncentiveReward, IrrigationClimateLog
from app.services import advisory, delivery_outbox as outbox, sms


def enable_live(monkeypatch):
    settings = Settings(_env_file=None, environment="development", allow_live_messages=True,
                        sms_provider="africas_talking", airtime_provider="africas_talking",
                        incentive_every_n_reports=1, incentive_max_per_day=10)
    monkeypatch.setattr(sms, "get_settings", lambda: settings)
    monkeypatch.setattr(advisory, "get_settings", lambda: settings)
    monkeypatch.setattr(outbox, "get_settings", lambda: settings)
    return settings


def test_ordinary_sms_is_committed_before_send_and_claimed_once(db, session_factory, monkeypatch):
    enable_live(monkeypatch)
    sent = []
    monkeypatch.setattr(outbox, "send_sms", lambda phone, message: sent.append((phone, message)) or {"status": "sent", "provider_id": "accepted-1"})
    item = sms.deliver(db, "+250788000099", "Advice", "auto_reply")
    assert item.status == "queued" and sent == []
    db.commit()
    assert outbox.dispatch_one(session_factory, "sms") == "sent"
    assert outbox.dispatch_one(session_factory, "sms") == "empty"
    db.expire_all()
    assert item.delivery_attempts == 1 and item.provider_id == "accepted-1"
    assert sent == [("+250788000099", "Advice")]


def test_rollback_removes_queued_messages(db, session_factory, monkeypatch):
    enable_live(monkeypatch)
    sms.deliver(db, "+250788000099", "Advice", "auto_reply")
    db.flush()
    db.rollback()
    assert outbox.dispatch_one(session_factory, "sms") == "empty"


def test_airtime_is_queued_in_same_transaction_as_report(db, session_factory, monkeypatch):
    enable_live(monkeypatch)
    user = FieldUser(phone_number="+250788000099")
    db.add(user)
    db.commit()
    report = IrrigationClimateLog(reporter_id=user.id, rainfall_mm=4)
    db.add(report)
    db.flush()
    reward = advisory.maybe_reward(db, user)
    assert reward.status == "queued"
    db.rollback()
    assert db.scalar(select(IrrigationClimateLog)) is None
    assert db.scalar(select(IncentiveReward)) is None
    assert outbox.dispatch_one(session_factory, "airtime") == "empty"


def test_timeout_is_unknown_and_never_automatically_replayed(db, session_factory, monkeypatch):
    enable_live(monkeypatch)
    item = sms.deliver(db, "+250788000099", "Advice", "auto_reply")
    db.commit()
    calls = []
    def fail(*args):
        calls.append(args)
        raise TimeoutError("provider may have accepted")
    monkeypatch.setattr(outbox, "send_sms", fail)
    assert outbox.dispatch_one(session_factory, "sms") == "unknown"
    assert outbox.dispatch_one(session_factory, "sms") == "empty"
    db.expire_all()
    assert item.status == "unknown" and len(calls) == 1


def test_opt_out_after_queue_cancels_broadcast(db, session_factory, monkeypatch):
    enable_live(monkeypatch)
    user = FieldUser(phone_number="+250788000099", opted_out_at=datetime.now(timezone.utc))
    db.add(user)
    sms.deliver(db, user.phone_number, "Advice", "irrigation_schedule")
    db.commit()
    monkeypatch.setattr(outbox, "send_sms", lambda *_: (_ for _ in ()).throw(AssertionError("must not send")))
    assert outbox.dispatch_one(session_factory, "sms") == "cancelled"


def test_stale_claim_recovery_never_requeues(db, session_factory):
    item = AdvisoryMessage(phone_number="+250788000099", message="x", status="dispatching",
                           last_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=10))
    db.add(item)
    db.commit()
    assert outbox.mark_stale_claims_unknown(session_factory) == 1
    db.expire_all()
    assert item.status == "unknown"


def test_simulator_never_creates_live_queue(db, monkeypatch):
    enable_live(monkeypatch)
    with sms.simulation():
        item = sms.deliver(db, "+250788000099", "x", "auto_reply")
    assert item.status == "dry_run"
