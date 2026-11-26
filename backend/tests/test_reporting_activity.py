"""Receipt window boundaries, scope and simulator isolation."""
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import Cell, CitizenScienceLog, Cooperative, FieldUser, Sector

URL = "/api/v1/analytics/reporting-activity?start=2026-11-10&end=2026-11-11"


def test_receipt_comparison_kigali_boundaries_and_exclusions(client, district, session_factory):
    with session_factory() as db:
        for stamp, origin in (("2026-11-09T21:59:59", "field"),  # previous local day
                              ("2026-11-09T22:00:00", "field"),  # first instant
                              ("2026-11-11T21:59:59", "field"),  # last instant
                              ("2026-11-11T22:00:00", "field"),  # next day
                              ("2026-11-10T12:00:00", "simulator"),
                              ("2026-11-10T12:00:00", "demo")):
            db.add(CitizenScienceLog(cell_id=district["cell_id"], crop_type="Beans", data_origin=origin,
                                    created_at=datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)))
        db.commit()
    response = client.get(URL)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    data = response.json()
    assert (data["reports"], data["previous_reports"], data["change"]) == (2, 1, 1)
    assert data["previous_start"] == "2026-11-08" and data["previous_end"] == "2026-11-09"
    assert data["verified_reports"] == 0 and data["located_reports"] == 0
    assert data["demo_mode"] is True


def test_cooperative_membership_and_cell_filters_intersect(client, district, session_factory):
    with session_factory() as db:
        coop = Cooperative(name="Fixture cooperative", sector_id=district["sector_id"])
        db.add(coop)
        db.flush()
        member = db.scalar(select(FieldUser).order_by(FieldUser.id))
        member.cooperative_id = coop.id
        other = Sector(name="Other sector")
        db.add(other)
        db.flush()
        cell = Cell(name="Other cell", sector_id=other.id)
        db.add(cell)
        db.flush()
        coop_id, other_cell = coop.id, cell.id
        for reporter in (member.id, None):
            db.add(CitizenScienceLog(cell_id=district["cell_id"], reporter_id=reporter,
                                    crop_type="Beans", created_at=datetime(2026, 11, 10, tzinfo=timezone.utc)))
        db.commit()
    assert client.get(URL).json()["reports"] == 2
    assert client.get(f"{URL}&cooperative_id={coop_id}").json()["reports"] == 1
    assert client.get(f"{URL}&cooperative_id={coop_id}&cell_id={other_cell}").json()["reports"] == 0


def test_invalid_receipt_filters_are_rejected(client, district):
    assert client.get(URL + "&cell_id=9999").status_code == 422
    assert client.get(URL.replace("2026-11-10", "2026-11-12")).status_code == 422
    assert client.get(URL.replace("2026-11-10", "2024-11-10")).status_code == 422


def test_requested_cell_cannot_expand_officer_scope(district, session_factory):
    from datetime import date
    from app.core.security import Principal
    from app.db.models import UserRole
    from app.services.reporting_activity import activity

    with session_factory() as db:
        other = Sector(name="Restricted-out sector")
        db.add(other)
        db.flush()
        cell = Cell(name="Outside", sector_id=other.id)
        db.add(cell)
        db.flush()
        db.add(CitizenScienceLog(cell_id=cell.id, crop_type="Beans",
                                created_at=datetime(2026, 11, 10, tzinfo=timezone.utc)))
        db.commit()
        principal = Principal(name="scoped", role=UserRole.district_officer,
                              sector_ids=frozenset({district["sector_id"]}))
        result = activity(db, principal, date(2026, 11, 10), date(2026, 11, 11), cell_id=cell.id)
        assert result["reports"] == result["previous_reports"] == result["located_reports"] == 0


def test_monitor_cannot_bypass_the_staff_cooperative_filter(client, district, auth):
    from app.db.models import UserRole
    headers = auth("activity-monitor@example.org", role=UserRole.citizen_science_monitor)
    assert client.get(URL, headers=headers).status_code == 200
    assert client.get(URL + "&cooperative_id=1", headers=headers).status_code == 403


def test_out_of_area_cooperative_is_indistinguishable_from_unknown(client, district, auth, session_factory):
    from app.db.models import PlatformAccount, UserRole
    headers = auth("activity-officer@example.org", role=UserRole.district_officer)
    with session_factory() as db:
        account = db.scalar(select(PlatformAccount).where(PlatformAccount.email == "activity-officer@example.org"))
        account.sectors = [db.get(Sector, district["sector_id"])]
        other = Sector(name="Unassigned sector")
        db.add(other)
        db.flush()
        cooperative = Cooperative(name="Out-of-area cooperative", sector_id=other.id)
        db.add(cooperative)
        db.commit()
        cooperative_id = cooperative.id
    existing = client.get(URL + f"&cooperative_id={cooperative_id}", headers=headers)
    unknown = client.get(URL + "&cooperative_id=9999", headers=headers)
    assert existing.status_code == unknown.status_code == 404
    assert existing.json() == unknown.json()
