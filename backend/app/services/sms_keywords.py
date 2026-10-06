"""SMS keyword channel on 8448 (architecture Module 1 and Module 2).

Examples a farmer can text:
    NYAMATA NZANA 4        fall armyworm in Nyamata, severity 4 (sector name is optional)
    INDWARA IBISHYIMBO     disease on beans
    IMVURA 12              12 mm of rain at my gauge today
    UMUSARURO IBIGORI 2.5  expected maize harvest of 2.5 tons
    IKIBAZO <message>      anonymous grievance
Anything else receives a short help message.
"""
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Cell, CommunityFeedback, Sector, User
from app.services.advisory import local_tip, maybe_reward
from app.services.reporting import create_crop_report, create_irrigation_report, scheme_for_cell

CROP_WORDS = {"UMUCERI": "Rice", "IBIGORI": "Maize", "IBISHYIMBO": "Beans", "IMYUMBATI": "Cassava", "IMBOGA": "Vegetables",
              "RICE": "Rice", "MAIZE": "Maize", "BEANS": "Beans", "CASSAVA": "Cassava", "VEGETABLES": "Vegetables"}
HELP = ("CS-IRCFS: Andika NZANA <ubukana 1-5>, INDWARA <igihingwa>, IMVURA <mm>, UMUSARURO <igihingwa> <toni>, "
        "cyangwa IKIBAZO <ubutumwa>. Cyangwa kanda *801#.")


@dataclass
class SmsResult:
    reply: str
    record_type: str | None = None
    record_id: int | None = None


def _number(token: str) -> float | None:
    try:
        return float(token.replace(",", "."))
    except ValueError:
        return None


def _sector_location(db: Session, words: list[str]) -> tuple[int | None, float | None, float | None, list[str]]:
    """Find a sector name anywhere in the message, e.g. 'Nyamata Nzana'."""
    sectors = {name.upper(): (sector_id, lat, lng) for sector_id, name, lat, lng in db.execute(select(Sector.id, Sector.name, Sector.latitude, Sector.longitude))}
    for index, word in enumerate(words):
        if word in sectors:
            sector_id, lat, lng = sectors[word]
            return sector_id, lat, lng, words[:index] + words[index + 1:]
    return None, None, None, words


def handle(db: Session, user: User, text: str) -> SmsResult:
    """Parse one inbound SMS and create the matching record. The caller commits."""
    words = (text or "").upper().replace(",", " ").split()
    sector_id, latitude, longitude, words = _sector_location(db, words)
    if not words:
        return SmsResult(HELP)
    keyword, args = words[0], words[1:]
    cell_id = user.cell_id
    if sector_id:
        user_sector = db.scalar(select(Cell.sector_id).where(Cell.id == cell_id)) if cell_id else None
        if user_sector == sector_id:
            latitude = longitude = None  # the reporter's own cell is more precise than the sector centroid
        else:
            # Reported for another sector: place it at the sector centroid, or its first cell if no centroid.
            cell_id = None if latitude is not None else db.scalar(
                select(Cell.id).where(Cell.sector_id == sector_id).order_by(func.lower(Cell.name)).limit(1))
    location = {"cell_id": cell_id, "latitude": latitude, "longitude": longitude}

    if keyword in {"NZANA", "ARMYWORM"}:
        severity = next((int(n) for n in map(_number, args) if n is not None and 1 <= n <= 5), 3)
        report = create_crop_report(db, reporter_id=user.id, scheme_id=scheme_for_cell(db, cell_id), crop_type="Maize",
                                    pest_or_disease="Fall armyworm", severity=severity, notes=f"SMS: {text.strip()}", **location)
        alert = " Abashinzwe ubuhinzi bamenyeshejwe." if severity >= 4 else ""
        return SmsResult(f"Murakoze! Raporo ya Nzana #{report.id} yakiriwe (ubukana {severity}).{alert}", "crop_report", report.id)

    if keyword == "INDWARA":
        crop = next((CROP_WORDS[w] for w in args if w in CROP_WORDS), "Unspecified crop")
        report = create_crop_report(db, reporter_id=user.id, scheme_id=scheme_for_cell(db, cell_id), crop_type=crop,
                                    pest_or_disease="Crop disease", severity=3, notes=f"SMS: {text.strip()}", **location)
        return SmsResult(f"Murakoze! Raporo y'indwara #{report.id} yakiriwe. Umujyanama w'ubuhinzi azabasura.", "crop_report", report.id)

    if keyword in {"IMVURA", "RAIN"}:
        mm = next((n for n in map(_number, args) if n is not None and 0 <= n <= 500), None)
        if mm is None:
            return SmsResult("Andika IMVURA ukurikizeho mm, urugero: IMVURA 12")
        report = create_irrigation_report(db, reporter_id=user.id, scheme_id=scheme_for_cell(db, cell_id), infrastructure_name="Citizen rain gauge",
                                          rainfall_mm=mm, **location)
        reward = maybe_reward(db, user)
        bonus = f" Wahawe {reward.amount_rwf} RWF y'itumanaho." if reward else ""
        return SmsResult(f"Murakoze! Imvura {mm:g} mm yanditswe.{bonus} {local_tip(db, user)}", "irrigation_report", report.id)

    if keyword in {"UMUSARURO", "HARVEST"}:
        crop = next((CROP_WORDS[w] for w in args if w in CROP_WORDS), None)
        tons = next((n for n in map(_number, args) if n is not None and 0 <= n <= 999), None)
        if not crop or tons is None:
            return SmsResult("Andika: UMUSARURO <igihingwa> <toni>, urugero: UMUSARURO IBIGORI 2.5")
        report = create_crop_report(db, reporter_id=user.id, scheme_id=scheme_for_cell(db, cell_id), crop_type=crop,
                                    expected_harvest_tons=tons, notes=f"SMS: {text.strip()}", **location)
        return SmsResult(f"Murakoze! Umusaruro #{report.id} wanditswe. {local_tip(db, user)}", "crop_report", report.id)

    if keyword in {"IKIBAZO", "IGITEKEREZO", "COMPLAINT"}:
        original = text.split()
        keyword_index = next(i for i, word in enumerate(original) if word.upper().strip(",") == keyword)
        message = " ".join(original[keyword_index + 1:])
        if len(message) < 5:
            return SmsResult("Andika IKIBAZO ukurikizeho ubutumwa bwawe.")
        feedback = CommunityFeedback(reporter_id=None, cell_id=cell_id, scheme_id=scheme_for_cell(db, cell_id),
                                     category="SMS Grievance", message=message[:3000], latitude=latitude, longitude=longitude)
        db.add(feedback)
        db.flush()
        return SmsResult(f"Murakoze. Ikibazo FB-{feedback.id:03d} cyakiriwe. Izina ryawe ntirizagaragazwa.", "community_feedback", feedback.id)

    return SmsResult(HELP)
