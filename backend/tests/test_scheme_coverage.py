from sqlalchemy import select

from app.db.models import Cell, IrrigationScheme, Sector
from app.services.reporting import scheme_for_cell


def test_multi_sector_coverage_matches_reports_and_never_guesses(client, district, db):
    second = Sector(name="Mareba")
    db.add(second)
    db.flush()
    cell = Cell(name="Second cell", sector_id=second.id)
    db.add(cell)
    db.commit()
    scheme = db.scalar(select(IrrigationScheme).where(IrrigationScheme.name == "APEFA Solar"))
    response = client.patch(f"/api/v1/irrigation-schemes/{scheme.id}", json={
        "coverage_sector_ids": [district["sector_id"], second.id]})
    assert response.status_code == 200
    assert response.json()["coverage_sector_ids"] == [district["sector_id"], second.id]
    db.expire_all()
    assert scheme_for_cell(db, cell.id) == scheme.id
    competing = client.post("/api/v1/irrigation-schemes", json={
        "name": "Overlapping scheme", "coverage_sector_ids": [second.id]})
    assert competing.status_code == 201
    assert scheme_for_cell(db, cell.id) is None
    client.patch(f'/api/v1/irrigation-schemes/{competing.json()["id"]}', json={"is_active": False})
    assert scheme_for_cell(db, cell.id) == scheme.id


def test_coverage_validation_is_atomic_and_can_clear_legacy_sector(client, district, db):
    scheme_id = db.scalar(select(IrrigationScheme.id).where(IrrigationScheme.name == "APEFA Solar"))
    url = f"/api/v1/irrigation-schemes/{scheme_id}"
    for invalid in ([999999], [district["sector_id"], district["sector_id"]], None):
        result = client.patch(url, json={"coverage_sector_ids": invalid, "implementing_partner": "must not save"})
        assert result.status_code == 422
    db.expire_all()
    assert db.get(IrrigationScheme, scheme_id).implementing_partner is None
    result = client.patch(url, json={"coverage_sector_ids": []})
    assert result.status_code == 200
    assert result.json()["sector_id"] is None
    assert result.json()["coverage_sector_ids"] == []
    assert scheme_for_cell(db, district["cell_id"]) is None
