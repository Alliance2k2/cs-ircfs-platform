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
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Cell, CommunityFeedback, FieldUser, Sector
from app.services.advisory import local_tip, maybe_reward
from app.services.reporting import add_months, create_crop_report, create_irrigation_report, scheme_for_cell
from app.services.ussd import varieties_for

CROP_WORDS = {"UMUCERI": "Rice", "IBIGORI": "Maize", "IBISHYIMBO": "Beans", "IMYUMBATI": "Cassava", "IMBOGA": "Vegetables",
              "RICE": "Rice", "MAIZE": "Maize", "BEANS": "Beans", "CASSAVA": "Cassava", "VEGETABLES": "Vegetables"}
HELP = ("CS-IRCFS: NZANA <ubukana 1-5>, INDWARA <igihingwa>, IMVURA <mm>, UMUSARURO <igihingwa> <toni> [UKWEZI <n>], "
        "IKIBAZO <ubutumwa>. Kanda *801#.")
# Optional yield-forecaster tokens on UMUSARURO (WP1): variety, months until harvest,
# months since planting. Old messages without them keep working.
# RW: needs field review
HARVEST_TOKENS = {"UKWEZI": "harvest_months", "HARVEST": "harvest_months", "MONTHS": "harvest_months",
                  "IMBERE": "planted_months", "PLANTED": "planted_months"}
VARIETY_TOKENS = {"IBUZI", "VARIETY"}


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


def _harvest_fields(args: list[str]) -> tuple[float | None, str | None, int | None, int | None]:
    """Parse optional yield-forecaster tokens: (tons, variety, harvest months, planted months).

    The first bare number stays the expected tons, so ``UMUSARURO IBIGORI 2.5 UKWEZI 3``
    records 2.5 t with harvest in 3 months, while the original two-word form is unchanged.
    """
    tons: float | None = None
    variety: str | None = None
    harvest_months: int | None = None
    planted_months: int | None = None
    index = 0
    while index < len(args):
        token, following = args[index], args[index + 1] if index + 1 < len(args) else None
        if token in VARIETY_TOKENS and following:
            variety, index = following, index + 2
            continue
        if token in HARVEST_TOKENS and following is not None:
            value = _number(following)
            if value is not None and 0 <= value <= 36:
                if HARVEST_TOKENS[token] == "harvest_months":
                    harvest_months = int(value)
                else:
                    planted_months = min(int(value), 24)
                index += 2
                continue
        if tons is None and (value := _number(token)) is not None and 0 <= value <= 999:
            tons = value
        index += 1
    return tons, variety, harvest_months, planted_months


def _sector_location(db: Session, words: list[str]) -> tuple[int | None, float | None, float | None, list[str]]:
    """Find a sector name anywhere in the message, e.g. 'Nyamata Nzana'."""
    sectors = {name.upper(): (sector_id, lat, lng) for sector_id, name, lat, lng in db.execute(select(Sector.id, Sector.name, Sector.latitude, Sector.longitude))}
    for index, word in enumerate(words):
        if word in sectors:
            sector_id, lat, lng = sectors[word]
            return sector_id, lat, lng, words[:index] + words[index + 1:]
    return None, None, None, words


def handle(db: Session, user: FieldUser, text: str) -> SmsResult:
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
        tons, variety, harvest_months, planted_months = _harvest_fields(args)
        if not crop or tons is None:
            return SmsResult("Andika: UMUSARURO <igihingwa> <toni>, urugero: UMUSARURO IBIGORI 2.5. Cyangwa ongeza UKWEZI <n>.")
        # Resolve the variety token against the crop's list; an unknown word is kept as typed
        # so a real variety name from the field is not thrown away.
        variety_rw = variety_en = None
        if variety:
            match = next(((rw, english) for rw, english in varieties_for(crop)
                          if variety in {rw.upper(), english.upper().split()[0], english.upper()}), None)
            variety_rw, variety_en = match if match else (variety, variety)
        report = create_crop_report(db, reporter_id=user.id, scheme_id=scheme_for_cell(db, cell_id), crop_type=crop,
                                    crop_variety=variety_en,
                                    planting_date=add_months(date(date.today().year, date.today().month, 1), -planted_months) if planted_months is not None else None,
                                    expected_harvest_month=add_months(date.today(), harvest_months) if harvest_months is not None else None,
                                    expected_harvest_tons=tons, notes=f"SMS: {text.strip()}", **location)
        extra = []
        if variety_rw:
            extra.append(f"ibyiciro {variety_rw}")
        if harvest_months is not None:
            extra.append(f"isarura {add_months(date.today(), harvest_months).isoformat()}")
        detail = f" ({', '.join(extra)})" if extra else ""
        return SmsResult(f"Murakoze! Umusaruro #{report.id} wanditswe{detail}. {local_tip(db, user)}", "crop_report", report.id)

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
