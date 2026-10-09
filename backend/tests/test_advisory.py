"""Irrigation advice thresholds and airtime incentives."""
from app.core.config import Settings
from app.db.models import FieldUser, IrrigationClimateLog, NutritionSurvey
from app.services import advisory


def incentive_settings(**overrides) -> Settings:
    return Settings(_env_file=None, dry_spell_threshold_mm=10, wet_spell_threshold_mm=40, **overrides)


def test_advice_for_rainfall_levels(monkeypatch):
    monkeypatch.setattr(advisory, "get_settings", lambda: incentive_settings())
    assert advisory.advice_for_rainfall(5, 1).level == "irrigate_more"
    assert advisory.advice_for_rainfall(50, 1).level == "irrigate_less"
    assert advisory.advice_for_rainfall(25, 1).level == "normal"
    assert advisory.advice_for_rainfall(None, 0).level == "no_data"


def test_airtime_reward_only_on_every_third_report(db):
    user = FieldUser(phone_number="+250788000001")
    db.add(user)
    db.commit()
    for _ in range(2):
        db.add(IrrigationClimateLog(reporter_id=user.id, rainfall_mm=1))
        db.commit()
        assert advisory.maybe_reward(db, user) is None
    db.add(IrrigationClimateLog(reporter_id=user.id, rainfall_mm=1))
    db.commit()
    reward = advisory.maybe_reward(db, user)
    assert reward is not None
    assert reward.amount_rwf == 100
    assert reward.status == "dry_run"


def survey(db, user) -> NutritionSurvey:
    row = NutritionSurvey(reporter_id=user.id, meals_per_day=2, ate_protein_or_vegetables=True,
                          food_sufficient=True, stunting_risk_score=2)
    db.add(row)
    db.commit()
    return row


def test_nutrition_survey_earns_airtime_on_every_third_report(db, monkeypatch):
    """WP4: nutrition counts towards the reward when INCENTIVE_REPORT_TYPES includes it."""
    monkeypatch.setattr(advisory, "get_settings", lambda: incentive_settings())
    user = FieldUser(phone_number="+250788000001")
    db.add(user)
    db.commit()
    for _ in range(2):
        survey(db, user)
        assert advisory.maybe_reward(db, user, from_nutrition_survey=True) is None
    survey(db, user)
    reward = advisory.maybe_reward(db, user, from_nutrition_survey=True)
    assert reward is not None and reward.amount_rwf == 100
    assert "nutrition survey" in reward.reason


def test_nutrition_reward_capped_per_month(db, monkeypatch):
    """WP4: at most one rewarded nutrition survey per household per month."""
    monkeypatch.setattr(advisory, "get_settings", lambda: incentive_settings(incentive_every_n_reports=1))
    user = FieldUser(phone_number="+250788000001")
    db.add(user)
    db.commit()
    survey(db, user)
    first = advisory.maybe_reward(db, user, from_nutrition_survey=True)
    assert first is not None
    db.commit()
    survey(db, user)
    assert advisory.maybe_reward(db, user, from_nutrition_survey=True) is None


def test_nutrition_not_rewarded_when_type_disabled(db, monkeypatch):
    """WP4: configuration decides which types count."""
    monkeypatch.setattr(advisory, "get_settings", lambda: incentive_settings(incentive_report_types="rainfall"))
    user = FieldUser(phone_number="+250788000001")
    db.add(user)
    db.commit()
    for _ in range(3):
        survey(db, user)
    assert advisory.maybe_reward(db, user, from_nutrition_survey=True) is None
    assert advisory.incentivised_report_count(db, user) == 0


def test_nutrition_reward_shows_in_ussd_reply(client, session_factory):
    """WP4: the USSD nutrition flow shows the airtime line once the threshold is met."""
    from sqlalchemy import select

    from app.db.models import IncentiveReward, FieldUser

    phone = "+250788000123"
    for index in range(3):
        response = client.post("/api/v1/ussd", data={"sessionId": f"nut-{index}", "phoneNumber": phone, "text": "6*2*1*1"})
    assert "Wahawe" in response.text
    with session_factory() as session:
        user = session.scalar(select(FieldUser).where(FieldUser.phone_number == phone))
        rewards = session.scalars(select(IncentiveReward).where(IncentiveReward.field_user_id == user.id)).all()
        assert len(rewards) == 1 and "nutrition survey" in rewards[0].reason
