"""USSD menu: first-time registration, harvest yield inputs, severe pests, and anonymity."""
from datetime import date

from sqlalchemy import select

from app.db.models import CitizenScienceLog, CommunityFeedback, FieldUser


def dial(client, text, phone="+250788000001", session="s1"):
    return client.post("/api/v1/ussd", data={"sessionId": session, "serviceCode": "*801#", "phoneNumber": phone, "text": text})


def test_unknown_caller_is_asked_for_a_location(client, district):
    response = dial(client, "", phone="0788 999 111")
    assert response.text.startswith("CON") and "Hitamo umurenge" in response.text


def test_full_new_caller_registration_then_harvest(client, district, session_factory):
    phone = "0788 999 111"
    # Each keypress belongs to its own session, as the gateway sends them.
    assert "Hitamo umurenge" in dial(client, "", phone=phone, session="r1").text
    assert "Gihembe" in dial(client, "1", phone=phone, session="r1").text
    assert dial(client, "1*1", phone=phone, session="r1").text.startswith("END Murakoze! Aho utuye habitswe: Gihembe, Ngeruka")
    # A later session goes straight to the main menu, and the report uses the stored location.
    assert "CS-IRCFS" in dial(client, "", phone=phone, session="r2").text
    # 1=harvest, 2=Maize, 1=improved seed, 1=planted this month, 8 weeks to harvest, 8 tons.
    assert dial(client, "1*2*1*1*8*8", phone=phone, session="r2").text.startswith("END Murakoze")
    with session_factory() as session:
        user = session.scalar(select(FieldUser).where(FieldUser.phone_number == "+250788999111"))
        assert user.cell_id == district["cell_id"]
        report = session.scalar(select(CitizenScienceLog).where(CitizenScienceLog.reporter_id == user.id))
        assert report.crop_type == "Maize" and report.expected_harvest_tons == 8
        assert report.crop_variety == "Improved seed" and report.planting_date is not None
        assert report.expected_harvest_month is not None


def test_option2_severity5_creates_a_critical_case(client):
    dial(client, "2*2*1*5")
    queue = client.get("/api/v1/analytics/act-now").json()
    assert any(item["priority"] == "critical" and "Fall armyworm" in item["title"] for item in queue)


def test_harvest_walks_every_step_in_order(client, session_factory):
    assert "Hitamo igihingwa" in dial(client, "1").text
    assert "Ibyiciro" in dial(client, "1*2").text          # variety screen after the crop
    assert "Wagutse igihe ki" in dial(client, "1*2*2").text  # planting month after the variety
    assert "ibyumweru" in dial(client, "1*2*2*3").text       # weeks until harvest
    assert "toni" in dial(client, "1*2*2*3*6").text          # expected tons last
    response = dial(client, "1*2*2*3*6*4.5")
    assert response.text.startswith("END Murakoze")
    with session_factory() as session:
        report = session.scalar(select(CitizenScienceLog))
        assert report.crop_type == "Maize" and report.crop_variety == "Local seed"
        assert report.expected_harvest_tons == 4.5
        # Planting month is stored as the first day of the month two months ago.
        today = date.today()
        total = today.month - 1 - 2
        year, month = today.year + total // 12, total % 12 + 1
        assert report.planting_date == date(year, month, 1)
        assert report.expected_harvest_month == date.fromordinal(today.toordinal() + 6 * 7)


def test_harvest_rejects_every_invalid_answer(client):
    assert dial(client, "1*9").text.startswith("END")            # no such crop
    assert dial(client, "1*2*9").text.startswith("END")         # no such variety
    assert dial(client, "1*2*2*9").text.startswith("END")       # no such planting month
    assert "ibyumweru" in dial(client, "1*2*2*3").text           # weeks prompt
    assert dial(client, "1*2*2*3*abc").text.startswith("END")    # weeks must be numeric
    assert dial(client, "1*2*2*3*999").text.startswith("END")    # weeks out of range
    assert dial(client, "1*2*2*3*6*xyz").text.startswith("END")  # tons must be numeric
    assert dial(client, "1*2*2*3*6*9999").text.startswith("END")  # tons out of range


def test_grievance_reporter_is_never_stored(client, session_factory):
    dial(client, "5*2*The water fee doubled this season")
    with session_factory() as session:
        feedback = session.scalar(select(CommunityFeedback))
    assert feedback.category == "Water Pricing" and feedback.reporter_id is None


def test_retry_with_same_session_records_once(client):
    payload = {"sessionId": "retry-1", "phoneNumber": "+250788000001", "text": "3*12"}
    first = client.post("/api/v1/ussd?explain=true", json=payload).json()
    retry = client.post("/api/v1/ussd?explain=true", json=payload).json()
    assert retry["reply_status"] == "duplicate"
    assert retry["record_id"] == first["record_id"]
    assert len(client.get("/api/v1/irrigation-reports").json()) == 1
