"""Act Now queue, case workflow, history, closing-the-loop, and area scoping."""
from sqlalchemy import select

from app.db.models import AdvisoryMessage, PlatformAccount, Sector, UserRole


def two_cases(client):
    """A critical and a high case, in that order of priority."""
    client.post("/api/v1/citizen-reports", json={"crop_type": "Maize", "pest_or_disease": "Fall armyworm", "severity": 5})
    client.post("/api/v1/citizen-reports", json={"crop_type": "Beans", "pest_or_disease": "Aphids", "severity": 4})
    return client.get("/api/v1/analytics/act-now").json()


def test_act_now_returns_open_cases_sorted_by_priority(client):
    queue = two_cases(client)
    assert [item["priority"] for item in queue] == ["critical", "high"]


def test_resolving_a_case_removes_it_from_the_queue(client):
    queue = two_cases(client)
    case_id = queue[0]["item_id"]
    assert client.patch(f"/api/v1/cases/{case_id}", json={"status": "resolved", "action_taken": "Sprayed"}).status_code == 200
    remaining = client.get("/api/v1/analytics/act-now").json()
    assert all(item["item_id"] != case_id for item in remaining)


def test_case_history_grows_by_one_per_status_change(client):
    queue = two_cases(client)
    case_id = queue[0]["item_id"]
    client.patch(f"/api/v1/cases/{case_id}", json={"status": "triaged"})
    client.patch(f"/api/v1/cases/{case_id}", json={"status": "in_progress"})
    assert len(client.get(f"/api/v1/cases/{case_id}/history").json()) == 2


def test_close_loop_sms_queues_one_message_per_cell_resident(client, district, session_factory):
    client.post("/api/v1/feedback", json={"category": "Water access", "message": "Canal blocked", "cell_id": district["cell_id"]})
    feedback_id = client.get("/api/v1/feedback").json()[0]["id"]
    client.patch(f"/api/v1/feedback/{feedback_id}", json={"status": "resolved", "action_taken": "Canal cleared"})
    result = client.post(f"/api/v1/feedback/{feedback_id}/notify-cell", json={}).json()
    assert result["sent"] == 2
    with session_factory() as session:
        queued = list(session.scalars(select(AdvisoryMessage).where(AdvisoryMessage.purpose == "close_loop")))
    assert len(queued) == 2


def test_area_scoped_principal_only_sees_cases_in_their_cells(client, district, session_factory, monkeypatch):
    from app.core.config import Settings
    from app.db.models import Cell

    with session_factory() as session:
        other = Sector(name="Nyamata")
        session.add(other)
        session.flush()
        far_cell = Cell(name="Kanazi", sector_id=other.id)
        session.add(far_cell)
        session.commit()
        far_cell_id = far_cell.id

    # Seed both cases while local development bypass is still active.
    client.post("/api/v1/citizen-reports", json={"cell_id": district["cell_id"], "crop_type": "Maize", "pest_or_disease": "Fall armyworm", "severity": 5})
    client.post("/api/v1/citizen-reports", json={"cell_id": far_cell_id, "crop_type": "Beans", "pest_or_disease": "Aphids", "severity": 5})

    # Now require real sign-in and give an officer access to only the Ngeruka sector.
    import app.core.security as security

    monkeypatch.setattr(security, "get_settings", lambda: Settings(_env_file=None, environment="production", require_api_key=True, api_key_roles=""))
    client.post("/api/v1/auth/register", json={"email": "o@example.org", "password": "Str0ng!pass", "first_name": "O", "surname": "F"})
    with session_factory() as session:
        account = session.scalar(select(PlatformAccount).where(PlatformAccount.email == "o@example.org"))
        account.role = UserRole.district_officer
        account.status = "active"  # self-registered accounts wait for approval
        account.sectors = [session.get(Sector, district["sector_id"])]
        session.commit()
    token = client.post("/api/v1/auth/login", json={"email": "o@example.org", "password": "Str0ng!pass"}).json()["access_token"]

    cases = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(cases) == 1
