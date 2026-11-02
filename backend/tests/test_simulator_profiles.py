from sqlalchemy import select

from app.db.models import FieldUser, InboundMessage
from app.services.advisory import sector_recipients


def test_training_cannot_opt_out_register_or_count_real_callers(client, district, db):
    original = db.scalar(select(FieldUser).where(FieldUser.phone_number == "+250788000001"))
    original.consent_at = None
    db.commit()
    before = client.get("/api/v1/public/overview").json()["farmers"]
    result = client.post("/api/v1/simulator/sms", json={"from": original.phone_number, "text": "STOP"})
    assert result.status_code == 200
    db.expire_all()
    assert original.opted_out_at is None and original.consent_at is None
    profile = db.scalar(select(FieldUser).where(FieldUser.data_origin == "simulator"))
    assert profile.phone_number.startswith("sim-") and profile.opted_out_at is not None
    assert profile.is_active is False
    assert client.get("/api/v1/public/overview").json()["farmers"] == before
    assert profile.id not in [row["id"] for row in client.get("/api/v1/field-users").json()]
    assert client.patch(f"/api/v1/field-users/{profile.id}", json={"is_active": True}).status_code == 404
    # Exclusion is source-based even if a profile is activated accidentally by a script.
    profile.cell_id = district["cell_id"]
    profile.is_active = True
    profile.opted_out_at = None
    db.commit()
    assert profile.phone_number not in [phone for phone, _ in sector_recipients(db, district["sector_id"])]


def test_training_registration_does_not_locate_a_real_profile(client, district, db):
    phone = "+250788998877"
    response = client.post("/api/v1/simulator/ussd", json={"phoneNumber": phone, "sessionId": "register", "text": "1*1"})
    assert response.status_code == 200
    assert response.json()["record_type"] == "location"
    assert db.scalar(select(FieldUser).where(FieldUser.phone_number == phone)) is None
    training = db.scalar(select(FieldUser).where(FieldUser.data_origin == "simulator"))
    assert training.cell_id == district["cell_id"]
    live = client.post("/api/v1/ussd", data={"phoneNumber": phone, "sessionId": "live", "text": ""})
    assert "Hitamo umurenge" in live.text
    real = db.scalar(select(FieldUser).where(FieldUser.phone_number == phone))
    assert real.cell_id is None


def test_training_and_live_gateway_retry_ids_do_not_collide(client, district, db):
    payload = {"from": "+250788000001", "text": "IMVURA 7", "id": "same-provider-id"}
    training = client.post("/api/v1/simulator/sms", json=payload).json()
    real = client.post("/api/v1/sms/inbound", data=payload).json()
    assert training["reply_status"] == real["reply_status"] == "dry_run"
    assert training["record_id"] != real["record_id"]
    assert set(db.scalars(select(InboundMessage.data_origin))) == {"simulator", "field"}
