"""Regressions for provider status correlation and explicit operator reconciliation."""
from sqlalchemy import select, func
from app.core.config import Settings
from app.db.models import AdvisoryMessage, DeliveryReceipt, AuditEvent
from app.services.delivery_receipts import apply_receipts
import app.api.routes.delivery as routes

TOKEN="r"*32


def enable(monkeypatch):
    monkeypatch.setattr(routes,"get_settings",lambda:Settings(_env_file=None,gateway_callback_token=TOKEN))


def test_receipts_require_secret_even_when_inbound_gateway_is_open(client, db):
    row=AdvisoryMessage(phone_number="+250788000011",message="test",status="sent",provider_id="AT1")
    db.add(row);db.commit()
    assert client.post("/api/v1/delivery/sms",data={"id":"AT1","status":"Success"}).status_code==403
    db.expire_all();assert row.status=="sent"


def test_duplicate_and_late_receipts_cannot_regress_delivery(client,db,monkeypatch):
    enable(monkeypatch)
    row=AdvisoryMessage(phone_number="+250788000011",message="test",status="sent",provider_id="AT1")
    db.add(row);db.commit()
    for status in ("Success","Success","Submitted","Failed"):
        response=client.post(f"/api/v1/delivery/sms?token={TOKEN}",data={"id":"AT1","status":status})
        assert response.status_code==200
    db.expire_all();assert row.status=="delivered"
    assert db.scalar(select(func.count()).select_from(DeliveryReceipt))==3


def test_early_receipt_is_journaled_until_provider_id_is_known(client,db,monkeypatch):
    enable(monkeypatch)
    response=client.post(f"/api/v1/delivery/sms?token={TOKEN}",data={"id":"early","status":"Success"})
    assert response.json()=={"accepted":True,"matched":False}
    row=AdvisoryMessage(phone_number="+250788000011",message="test",status="sent",provider_id="early")
    db.add(row);db.flush();apply_receipts(db,"sms",row);db.commit()
    assert row.status=="delivered"
    assert db.scalar(select(DeliveryReceipt)).applied_at is not None


def test_unknown_status_or_bad_secret_is_rejected(client,monkeypatch):
    enable(monkeypatch)
    assert client.post("/api/v1/delivery/sms?token=bad",json={"id":"x","status":"Success"}).status_code==403
    assert client.post(f"/api/v1/delivery/sms?token={TOKEN}",json={"id":"x","status":"invented"}).status_code==422


def test_requeue_requires_provider_confirmation_and_is_audited(client,db):
    item=AdvisoryMessage(phone_number="+250788000011",message="test",status="unknown",provider_id="old")
    db.add(item);db.commit()
    url=f"/api/v1/delivery/sms/{item.id}/reconcile"
    assert client.post(url,json={"action":"requeue","reference":"Provider ticket 17"}).status_code==422
    result=client.post(url,json={"action":"requeue","reference":"Provider ticket 17","confirmed_not_sent":True})
    assert result.status_code==200 and result.json()["status"]=="queued"
    db.expire_all();assert item.provider_id is None
    assert db.scalar(select(AuditEvent).where(AuditEvent.action=="delivery.reconcile")) is not None


def test_delivery_operations_are_administrator_only(client,auth):
    from app.db.models import UserRole
    headers=auth("queue-monitor@example.org",role=UserRole.citizen_science_monitor)
    assert client.get("/api/v1/delivery/queue",headers=headers).status_code==403
