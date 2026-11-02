from datetime import datetime,timedelta,timezone
from cryptography.fernet import Fernet
from sqlalchemy import select
from app.core.config import Settings
from app.db.models import AdvisoryMessage
from app.services import sms,private_replies,delivery_outbox as outbox


def config(monkeypatch):
    settings=Settings(_env_file=None,environment="development",allow_live_messages=True,sms_provider="africas_talking",
        anonymous_reply_queue_enabled=True,anonymous_reply_policy_reference="DPO test policy",anonymous_reply_encryption_key=Fernet.generate_key().decode())
    for module in (sms,private_replies,outbox):monkeypatch.setattr(module,"get_settings",lambda:settings)
    return settings


def test_private_route_is_encrypted_and_erased_before_provider_call(db,session_factory,monkeypatch):
    config(monkeypatch)
    row=sms.deliver(db,"+250788123456","Reference FB1","auto_reply",anonymous=True)
    db.commit()
    assert row.phone_number=="withheld" and "+250788123456" not in row.private_recipient
    calls=[]
    def provider(phone,message):
        with session_factory() as other:
            stored=other.get(AdvisoryMessage,row.id)
            assert stored.private_recipient is None and stored.phone_number=="withheld"
        calls.append(phone)
        return {"status":"sent","provider_id":"private-1"}
    monkeypatch.setattr(outbox,"send_sms",provider)
    assert outbox.dispatch_one(session_factory,"sms")=="sent"
    assert calls==["+250788123456"]


def test_expired_private_route_is_erased_without_send(db,session_factory,monkeypatch):
    config(monkeypatch)
    row=sms.deliver(db,"+250788123456","Reference FB1","auto_reply",anonymous=True)
    row.private_recipient_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    db.commit()
    monkeypatch.setattr(outbox,"send_sms",lambda *_: (_ for _ in ()).throw(AssertionError("expired route must not send")))
    assert outbox.dispatch_one(session_factory,"sms")=="cancelled"
    db.expire_all();assert row.private_recipient is None


def test_optional_private_queue_requires_policy_and_key():
    import pytest
    with pytest.raises(RuntimeError,match="Fernet"):
        Settings(_env_file=None,anonymous_reply_queue_enabled=True).guard_runtime()
