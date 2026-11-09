from types import SimpleNamespace

from app.db.models import SchemeAsset
from app.services import ussd


def test_hosted_phone_menu_never_invents_a_scheme_inventory(client, district, db, monkeypatch):
    monkeypatch.setattr(ussd, "get_settings", lambda: SimpleNamespace(environment="staging"))
    assert ussd.asset_options(db) == []
    result = client.post("/api/v1/ussd", data={"phoneNumber": "+250788000001", "sessionId": "no-inventory", "text": "4"})
    assert result.status_code == 200 and result.text.startswith("END")
    assert "PADAB pompe" not in result.text
    assert client.get("/api/v1/irrigation-reports").json() == []


def test_retired_inventory_does_not_reappear_as_development_examples(db, monkeypatch):
    monkeypatch.setattr(ussd, "get_settings", lambda: SimpleNamespace(environment="development"))
    db.add(SchemeAsset(name_en="Synthetic retired pump", name_rw="Fixture", is_active=False))
    db.commit()
    assert ussd.asset_options(db) == []


def test_hosted_menu_uses_only_the_configured_active_inventory(db, monkeypatch):
    monkeypatch.setattr(ussd, "get_settings", lambda: SimpleNamespace(environment="production"))
    db.add(SchemeAsset(name_en="Synthetic configured pump", name_rw="Fixture", is_active=True))
    db.commit()
    assert [item[1] for item in ussd.asset_options(db)] == ["Synthetic configured pump"]
