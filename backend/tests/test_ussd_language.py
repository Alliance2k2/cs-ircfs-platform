"""USSD preference, replay and profile isolation; no live providers."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import CitizenScienceLog, FieldUser, IrrigationClimateLog, NutritionSurvey
from app.services import ussd


def call(client, text="", session="language", phone="+250788999111", simulator=False):
    payload = {"sessionId": session, "phoneNumber": phone, "text": text}
    response = client.post("/api/v1/simulator/ussd" if simulator else "/api/v1/ussd", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["response"] if simulator else response.text


@pytest.mark.parametrize("choice,language,title", [("1", "rw", "Kaze kuri"), ("2", "en", "Welcome to")])
def test_service_selects_and_renders_language_without_reports(db, choice, language, title):
    user = FieldUser(phone_number="+250788111222")
    db.add(user)
    db.flush()
    assert ussd.handle(db, user, "").response == "CON " + ussd.LANGUAGE_PROMPT[0]
    result = ussd.handle(db, user, choice, language_selection=True)
    assert result.response.startswith("CON " + title)
    assert "0." in result.response
    assert user.ussd_language == language and user.cell_id is None and user.consent_at is None
    assert result.record_id is None and result.record_type is None


@pytest.mark.parametrize("choice,language,sector,cell,saved,main", [
    ("1", "rw", "Hitamo umurenge", "hitamo akagari", "Aho utuye habitswe", "Kaze kuri"),
    ("2", "en", "Choose the sector", "choose your cell", "Your location is saved", "Welcome to"),
])
def test_language_then_location_same_session_and_returning_access(client, district, db, choice, language, sector, cell, saved, main):
    assert "Choose language" in call(client)
    assert sector in call(client, choice)
    assert cell in call(client, choice + "*1")
    assert saved in call(client, choice + "*1*1")
    assert main in call(client, session="returning")
    profile = db.scalar(select(FieldUser).where(FieldUser.phone_number == "+250788999111"))
    assert profile.ussd_language == language and profile.cell_id == district["cell_id"]
    assert db.scalar(select(func.count()).select_from(CitizenScienceLog)) == 0
    assert db.scalar(select(func.count()).select_from(IrrigationClimateLog)) == 0
    assert db.scalar(select(func.count()).select_from(NutritionSurvey)) == 0


@pytest.mark.parametrize("answer", ["", "3", "en", "\u00b2", "9" * 5000], ids=["blank", "unknown", "word", "superscript", "oversized"])
def test_invalid_language_does_not_save_preference(client, district, db, answer):
    call(client)
    reply = call(client, answer)
    assert reply.startswith("CON" if not answer else "END")
    profile = db.scalar(select(FieldUser).where(FieldUser.phone_number == "+250788999111"))
    assert profile.ussd_language is None and profile.cell_id is None
    assert "Choose language" in call(client, session="after-invalid")


def test_returning_language_change_preserves_consent_location_optout_and_science(client, district, db):
    user = db.scalar(select(FieldUser).where(FieldUser.phone_number == "+250788000001"))
    user.consent_at = None
    user.opted_out_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db.add(IrrigationClimateLog(reporter_id=user.id, cell_id=user.cell_id, rainfall_mm=12))
    db.commit()
    before = (user.cell_id, user.consent_at, user.opted_out_at, user.is_active, user.data_origin)
    assert "Choose language" in call(client, "0", phone=user.phone_number)
    selected = call(client, "0*2", phone=user.phone_number)
    assert selected.startswith("CON Welcome to") and "6. Household nutrition" in selected
    assert selected == call(client, "0*2", phone=user.phone_number)
    db.refresh(user)
    assert user.ussd_language == "en"
    assert (user.cell_id, user.consent_at, user.opted_out_at, user.is_active, user.data_origin) == before
    assert db.scalar(select(IrrigationClimateLog.rainfall_mm)) == 12
    assert "Welcome to" in call(client, session="next-call", phone=user.phone_number)
    assert "Kaze kuri" in call(client, "0*1", session="switch-back", phone=user.phone_number)


def test_old_language_prefix_replay_does_not_overwrite_newer_preference(client, district, db):
    call(client)
    original = call(client, "2")
    call(client, "0*1", session="new-choice")
    assert call(client, "2") == original
    assert "choose your cell" in call(client, "2*1")
    profile = db.scalar(select(FieldUser).where(FieldUser.phone_number == "+250788999111"))
    assert profile.ussd_language == "rw"


def test_simulator_language_and_callback_ids_cannot_modify_real_profile(client, district, db):
    phone = "+250788000001"
    real = db.scalar(select(FieldUser).where(FieldUser.phone_number == phone))
    real.consent_at = None
    db.commit()
    assert "Choose language" in call(client, phone=phone, simulator=True)
    assert "Choose the sector" in call(client, "2", phone=phone, simulator=True)
    call(client, "2*1", phone=phone, simulator=True)
    call(client, "2*1*1", phone=phone, simulator=True)
    db.refresh(real)
    assert real.ussd_language == "rw" and real.consent_at is None
    training = db.scalar(select(FieldUser).where(FieldUser.data_origin == "simulator"))
    assert training.ussd_language == "en" and training.id != real.id and not training.is_active
    assert "Kaze kuri" in call(client, phone=phone)


@pytest.mark.parametrize("language", ["rw", "en"])
@pytest.mark.parametrize("option,rw,en", [
    ("1", "Hitamo igihingwa", "Choose the crop"),
    ("2", "Igihingwa cyafashwe", "Which crop is affected"),
    ("4", "Hitamo igikorwa", "Choose the asset"),
    ("5", "Hitamo icyiciro", "Choose a category"),
    ("6", "Ejo urugo", "How many meals"),
])
def test_existing_reporting_prompts_use_selected_language(client, district, db, language, option, rw, en):
    user = db.scalar(select(FieldUser).where(FieldUser.phone_number == "+250788000001"))
    user.ussd_language = language
    db.commit()
    assert (rw if language == "rw" else en) in call(client, option, phone=user.phone_number)


@pytest.mark.parametrize("language,expected", [("rw", "yanditswe"), ("en", "recorded")])
def test_rainfall_validation_and_retry_in_both_languages(client, district, db, language, expected):
    user = db.scalar(select(FieldUser).where(FieldUser.phone_number == "+250788000001"))
    user.ussd_language = language
    db.commit()
    assert call(client, "3*nan", phone=user.phone_number).startswith("END")
    first = call(client, "3*12", session="valid", phone=user.phone_number)
    assert expected in first
    assert call(client, "3*12", session="valid", phone=user.phone_number) == first
    assert db.scalar(select(func.count()).select_from(IrrigationClimateLog)) == 1


def test_preference_is_database_constrained(db):
    db.add(FieldUser(phone_number="+250788111222", ussd_language="fr"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


@pytest.mark.parametrize("session", [None, "", " "])
def test_ussd_requires_session_id_before_registering(client, db, session):
    response = client.post("/api/v1/ussd", json={"phoneNumber": "+250788999111", "sessionId": session, "text": ""})
    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(FieldUser)) == 0
