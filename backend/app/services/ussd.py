"""Kinyarwanda-first USSD menu for *801# (architecture Sections 4 and 8.4).

Africa's Talking calls the callback once per keypress with the full answer path in
``text`` (for example ``"3*12"``), and expects a reply beginning with ``CON`` (show
another screen) or ``END`` (close the session). The menu is therefore stateless: the
path is replayed on every request.

Design rules from the architecture: numeric answers wherever possible, no free text
except the grievance message, and at most three levels below the main menu.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Cell, CommunityFeedback, FieldUser, GrievanceCategory, NutritionSurvey, SchemeAsset, Sector
from app.services.advisory import local_tip, maybe_reward, nutrition_risk_score
from app.services.reporting import add_months, create_crop_report, create_irrigation_report, scheme_by_prefix, scheme_for_cell

# (Kinyarwanda, English) pairs. Kinyarwanda wording should be reviewed with field teams.
MAIN = ("Kaze kuri CS-IRCFS. Hitamo:\n1. Rapora umusaruro\n2. Indwara/udukoko\n3. Rapora imvura\n4. Ibikorwa remezo byo kuhira\n5. Tanga ikibazo/igitekerezo\n6. Imirire y'urugo",
        "Welcome to CS-IRCFS. Choose:\n1. Report harvest\n2. Disease/pests\n3. Report rainfall\n4. Irrigation infrastructure\n5. Submit a grievance/feedback\n6. Household nutrition")

CROPS = [("Umuceri", "Rice"), ("Ibigori", "Maize"), ("Ibishyimbo", "Beans"), ("Imyumbati", "Cassava"), ("Imboga", "Vegetables")]
# Yield forecaster inputs (WP1): seed varieties per crop. Generic seed classes only — real
# variety names must come from district documents, so CROP_VARIETIES stays one editable
# structure (add "Maize": [("...", "...")] when the list is supplied).
# RW: needs field review
SEED_CLASSES = [("Ibyatunganye", "Improved seed"), ("Ibyera hafi", "Local seed"), ("Ntazi", "Other / unknown")]
CROP_VARIETIES: dict[str, list[tuple[str, str]]] = {}
# RW: needs field review
PLANTING_MONTHS = [("Uyu mwesi", "This month"), ("Ukwezi gushize", "Last month"),
                   ("Ukwezi 2 gushize", "2 months ago"), ("Ukwezi 3 gushize", "3 months or more ago")]
PESTS = [("Nzana", "Fall armyworm"), ("Indwara y'ibibabi", "Leaf disease"), ("Indwara y'imizi", "Root disease"), ("Ibindi byonnyi", "Other pest")]
SEVERITY = [("Buke", "Low"), ("Buringaniye", "Moderate"), ("Bukabije", "Serious"), ("Bukabije cyane", "Very serious"), ("Byangiritse byose", "Total loss")]
# Pre-populated from the PADAB and APEFA asset inventories (Section 9.2), so operators pick from a list.
ASSETS = [("PADAB pompe 1", "PADAB Pumping Station 1", "PADAB"), ("PADAB pompe 2", "PADAB Pumping Station 2", "PADAB"),
          ("PADAB umuyoboro", "PADAB canal network (65.5 km)", "PADAB"), ("APEFA pompe Ngeruka", "APEFA solar pump - Ngeruka", "APEFA"),
          ("APEFA pompe Mareba", "APEFA solar pump - Mareba", "APEFA")]
STATUS = [("Irakora neza", "Working well", "operational"), ("Ifite ikibazo", "Has a fault", "faulty"), ("Ntikora", "Not working", "offline")]
BOTTLENECKS = [("Tekiniki (imashini)", "Technical (machinery)", "technical"), ("Imibereho y'abaturage", "Social", "social"),
               ("Imiyoborere/inzego", "Institutional", "institutional"), ("Ibidukikije (isuri, imyanda)", "Environmental (erosion, silt)", "environmental")]
GRIEVANCES = [("Ikwirakwizwa ry'inyongeramusaruro", "Input Distribution"), ("Igiciro cy'amazi", "Water Pricing"),
              ("Kwimurwa/ingaruka z'urugomero", "Resettlement/Downstream Impact"), ("Imikorere y'umushinga", "Operational Challenge"),
              ("Ibindi", "Other")]
MEALS = [("Rimwe", "Once"), ("Kabiri", "Twice"), ("Gatatu cyangwa kurenga", "Three times or more")]
YES_NO = [("Yego", "Yes"), ("Oya", "No")]
# First call: a caller without a cell chooses sector and cell once, so every later report is mapped,
# linked to its scheme, and reaches closing-the-loop SMS for that cell.
SECTORS_PER_PAGE = 8
MORE_SECTORS = ("Indi mirenge", "Other sectors")
# Databases with more than 9 grievance categories or assets paginate the same way,
# so every screen keeps at most 9 choices (Section 9, WP7).
MENU_PAGE_SIZE = 8
# RW: needs field review
MORE_OPTIONS = ("Reba indi", "Show more")
INVALID = ("Igisubizo ntikemewe. Ongera ugerageze ukanda *801#.", "That answer is not valid. Please dial *801# again.")


@dataclass
class UssdResult:
    response: str
    english: str
    record_type: str | None = None
    record_id: int | None = None
    notes: list[str] = field(default_factory=list)


def menu(title: tuple[str, str], options: list[tuple]) -> tuple[str, str]:
    rw = title[0] + "\n" + "\n".join(f"{i}. {option[0]}" for i, option in enumerate(options, 1))
    en = title[1] + "\n" + "\n".join(f"{i}. {option[1]}" for i, option in enumerate(options, 1))
    return rw, en


def menu_page(title: tuple[str, str], options: list[tuple], page: int = 0) -> tuple[str, str]:
    """One screen of a possibly longer list: at most MENU_PAGE_SIZE choices plus 'Show more'."""
    start = page * MENU_PAGE_SIZE
    items = options[start:start + MENU_PAGE_SIZE]
    if len(options) > start + len(items):
        items = items + [MORE_OPTIONS]
    return menu(title, items)


def paged_pick(title: tuple[str, str], options: list[tuple], steps: list[str]):
    """Resolve a numbered answer against a menu that may span several screens.

    Returns ("screen", result) when the next page must be shown, ("invalid", None)
    for an answer outside the menu, or ("choice", option, remaining_steps).
    """
    page = 0
    while True:
        start = page * MENU_PAGE_SIZE
        items = options[start:start + MENU_PAGE_SIZE]
        has_more = len(options) > start + len(items)
        if not steps:
            return "screen", con(menu_page(title, options, page))
        if has_more and steps[0] == str(len(items) + 1):
            steps = steps[1:]
            page += 1
            continue
        choice = pick(items, steps[0])
        if not choice:
            return "invalid", None
        return "choice", choice, steps[1:]


def pick(options: list, answer: str):
    """Return the chosen option for a 1-based numeric answer, or None."""
    return options[int(answer) - 1] if answer.isdigit() and 1 <= int(answer) <= len(options) else None


def number(answer: str, low: float, high: float) -> float | None:
    try:
        value = float(answer.replace(",", "."))
    except ValueError:
        return None
    return value if low <= value <= high else None


def varieties_for(crop_english: str) -> list[tuple[str, str]]:
    """Numbered variety choices for a crop: its own list when supplied, else the seed classes."""
    return CROP_VARIETIES.get(crop_english) or SEED_CLASSES


def grievance_options(db: Session) -> list[tuple[str, str]]:
    """(Kinyarwanda, English) active grievance categories from the database (WP7),
    falling back to the built-in list when the table has not been seeded."""
    rows = db.scalars(
        select(GrievanceCategory)
        .where(GrievanceCategory.is_active.is_(True))
        .order_by(GrievanceCategory.sort_order, GrievanceCategory.id)
    )
    return [(row.label_rw, row.label_en) for row in rows] or GRIEVANCES


def asset_options(db: Session) -> list[tuple[str, str, object]]:
    """(Kinyarwanda, English, scheme id or scheme-name prefix) active assets from the
    database (WP7), falling back to the built-in PADAB/APEFA inventory."""
    rows = db.scalars(
        select(SchemeAsset).where(SchemeAsset.is_active.is_(True)).order_by(SchemeAsset.id)
    )
    return [(row.name_rw, row.name_en, row.scheme_id) for row in rows] or ASSETS


def con(screen: tuple[str, str]) -> UssdResult:
    return UssdResult("CON " + screen[0], screen[1])


def end(screen: tuple[str, str], record_type: str | None = None, record_id: int | None = None) -> UssdResult:
    return UssdResult("END " + screen[0], screen[1], record_type, record_id)


def handle(db: Session, user: FieldUser, text: str) -> UssdResult:
    """Route one USSD request. The caller commits the transaction."""
    steps = [step.strip() for step in text.split("*")] if text else []
    if user.cell_id is None:
        sectors = db.scalars(select(Sector).order_by(Sector.name)).all()
        if sectors:
            return set_location(db, user, sectors, steps)
    if not steps:
        return con(MAIN)
    flows = {"1": harvest, "2": pest, "3": rainfall, "4": infrastructure, "5": grievance, "6": nutrition}
    flow = flows.get(steps[0])
    return flow(db, user, steps[1:]) if flow else end(INVALID)


def set_location(db: Session, user: FieldUser, sectors: list[Sector], steps: list[str]) -> UssdResult:
    """Ask a first-time caller for sector then cell. 15 sectors fit on two screens."""
    first, rest = sectors[:SECTORS_PER_PAGE], sectors[SECTORS_PER_PAGE:]
    page_one = [(sector.name, sector.name) for sector in first] + ([MORE_SECTORS] if rest else [])
    if not steps:
        return con(menu(("Murakaza neza! Hitamo umurenge utuyemo:", "Welcome! Choose the sector where you live:"), page_one))
    if rest and steps[0] == str(len(page_one)):
        if len(steps) == 1:
            return con(menu(("Hitamo umurenge utuyemo:", "Choose the sector where you live:"), [(sector.name, sector.name) for sector in rest]))
        sector, steps = pick(rest, steps[1]), steps[2:]
    else:
        sector, steps = pick(first, steps[0]), steps[1:]
    if not sector:
        return end(INVALID)
    cells = db.scalars(select(Cell).where(Cell.sector_id == sector.id).order_by(Cell.name)).all()
    if not cells:
        return end(INVALID)
    if not steps:
        return con(menu((f"{sector.name}: hitamo akagari utuyemo:", f"{sector.name}: choose your cell:"), [(cell.name, cell.name) for cell in cells]))
    cell = pick(cells, steps[0])
    if not cell:
        return end(INVALID)
    user.cell_id = cell.id
    return end((f"Murakoze! Aho utuye habitswe: {cell.name}, {sector.name}.\nKanda *801# wongere utange raporo.",
                f"Thank you! Your location is saved: {cell.name}, {sector.name}.\nDial *801# again to send a report."), "location", user.id)


def harvest(db: Session, user: FieldUser, steps: list[str]) -> UssdResult:
    """Yield forecaster inputs (WP1): crop, variety, planting month, weeks to harvest, tons.

    Menu depth stays within the three-level rule: crop, variety and planting month are
    the numbered screens; weeks-to-harvest and tons are single numeric prompts.
    """
    if not steps:
        return con(menu(("Hitamo igihingwa:", "Choose the crop:"), CROPS))
    crop = pick(CROPS, steps[0])
    if not crop:
        return end(INVALID)
    varieties = varieties_for(crop[1])
    if len(steps) == 1:
        return con(menu((f"Ibyiciro bya {crop[0]}:", f"Variety of {crop[1]}:"), varieties))
    variety = pick(varieties, steps[1])
    if not variety:
        return end(INVALID)
    if len(steps) == 2:
        return con(menu(("Wagutse igihe ki?", "When was it planted?"), PLANTING_MONTHS))
    planted = pick(PLANTING_MONTHS, steps[2])
    if not planted:
        return end(INVALID)
    if len(steps) == 3:
        return con(("Andika ibyumweru dusigira kugera isarura, urugero 8",
                    "Enter the weeks until harvest, e.g. 8"))
    weeks = number(steps[3], 0, 104)
    if weeks is None:
        return end(INVALID)
    if len(steps) == 4:
        return con((f"{crop[0]}: andika umusaruro uteganyijwe (toni), urugero 2.5", f"{crop[1]}: enter the expected harvest (tons), e.g. 2.5"))
    tons = number(steps[4], 0, 999)
    if tons is None:
        return end(INVALID)
    # The answers are month-precision: planting is stored as the first day of that month,
    # "3 months or more" as 3 months, and harvest as today plus the weeks given.
    months_ago = PLANTING_MONTHS.index(planted)
    today = date.today()
    planting_date = add_months(date(today.year, today.month, 1), -months_ago)
    expected_harvest = today + timedelta(weeks=round(weeks))
    report = create_crop_report(db, reporter_id=user.id, cell_id=user.cell_id, scheme_id=scheme_for_cell(db, user.cell_id),
                                crop_type=crop[1], crop_variety=variety[1], planting_date=planting_date,
                                expected_harvest_month=expected_harvest, expected_harvest_tons=tons, notes="Submitted by USSD")
    tip = local_tip(db, user)
    return end((f"Murakoze! {crop[0]} ({variety[0]}) wanditswe: {tons} t, isarura {expected_harvest.isoformat()}. Nimero #{report.id}.\n{tip}",
                f"Thank you! {crop[1]} ({variety[1]}) recorded: {tons} t, harvest {expected_harvest.isoformat()}. #{report.id}.\n(Local tip sent in Kinyarwanda.)"), "crop_report", report.id)


def pest(db: Session, user: FieldUser, steps: list[str]) -> UssdResult:
    if not steps:
        return con(menu(("Igihingwa cyafashwe:", "Which crop is affected?"), CROPS))
    crop = pick(CROPS, steps[0])
    if not crop:
        return end(INVALID)
    if len(steps) == 1:
        return con(menu(("Hitamo ikibazo:", "Choose the problem:"), PESTS))
    problem = pick(PESTS, steps[1])
    if not problem:
        return end(INVALID)
    if len(steps) == 2:
        return con(menu(("Ubukana bw'ikibazo:", "How severe is it?"), SEVERITY))
    severity = int(steps[2]) if pick(SEVERITY, steps[2]) else None
    if severity is None:
        return end(INVALID)
    report = create_crop_report(db, reporter_id=user.id, cell_id=user.cell_id, scheme_id=scheme_for_cell(db, user.cell_id),
                                crop_type=crop[1], pest_or_disease=problem[1], severity=severity, notes="Submitted by USSD")
    alert = ("\nAbashinzwe ubuhinzi bamenyeshejwe.", "\nAgricultural officers have been alerted.") if severity >= 4 else ("", "")
    return end((f"Murakoze! Raporo #{report.id} ya {problem[0]} yakiriwe.{alert[0]}",
                f"Thank you! {problem[1]} report #{report.id} received.{alert[1]}"), "crop_report", report.id)


def reward_line(db: Session, user: FieldUser, from_nutrition_survey: bool = False) -> tuple[str, str]:
    reward = maybe_reward(db, user, from_nutrition_survey=from_nutrition_survey)
    if not reward:
        return "", ""
    return f"\nWahawe {reward.amount_rwf} RWF y'itumanaho. Murakoze!", f"\nYou earned {reward.amount_rwf} RWF airtime."


def rainfall(db: Session, user: FieldUser, steps: list[str]) -> UssdResult:
    if not steps:
        return con(("Andika imvura yaguye uyu munsi (mm), urugero 12", "Enter today's rainfall (mm), e.g. 12"))
    mm = number(steps[0], 0, 500)
    if mm is None:
        return end(INVALID)
    report = create_irrigation_report(db, reporter_id=user.id, cell_id=user.cell_id, scheme_id=scheme_for_cell(db, user.cell_id),
                                      infrastructure_name="Citizen rain gauge", rainfall_mm=mm)
    reward = reward_line(db, user)
    tip = local_tip(db, user)
    return end((f"Murakoze! Imvura {mm} mm yanditswe.{reward[0]}\n{tip}", f"Thank you! {mm} mm recorded.{reward[1]}"), "irrigation_report", report.id)


def infrastructure(db: Session, user: FieldUser, steps: list[str]) -> UssdResult:
    title = ("Hitamo igikorwa remezo:", "Choose the asset:")
    outcome = paged_pick(title, asset_options(db), steps)
    if outcome[0] == "screen":
        return outcome[1]
    if outcome[0] == "invalid":
        return end(INVALID)
    _, asset, steps = outcome
    if not steps:
        return con(menu(("Imiterere yacyo:", "Its condition:"), STATUS))
    status = pick(STATUS, steps[0])
    if not status:
        return end(INVALID)
    if status[2] != "operational" and len(steps) == 1:
        return con(menu(("Impamvu nyamukuru:", "Main cause:"), BOTTLENECKS))
    bottleneck = pick(BOTTLENECKS, steps[1]) if status[2] != "operational" else None
    if status[2] != "operational" and not bottleneck:
        return end(INVALID)
    # Database assets carry their scheme directly; the built-in fallback carries a name prefix.
    scheme_id = scheme_by_prefix(db, asset[2]) if isinstance(asset[2], str) else asset[2]
    report = create_irrigation_report(db, reporter_id=user.id, cell_id=user.cell_id, scheme_id=scheme_id,
                                      infrastructure_name=asset[1], operational_status=status[2],
                                      bottleneck_category=bottleneck[2] if bottleneck else None,
                                      fault_description=f"USSD report: {status[1]}" + (f", {bottleneck[1]}" if bottleneck else ""))
    reward = reward_line(db, user)
    if status[2] == "operational":
        return end((f"Murakoze! {asset[0]} yanditswe ko ikora neza.{reward[0]}", f"Thank you! {asset[1]} recorded as working.{reward[1]}"), "irrigation_report", report.id)
    return end((f"Murakoze! Ikibazo #{report.id} cya {asset[0]} cyoherejwe ku karere.{reward[0]}",
                f"Thank you! Fault #{report.id} on {asset[1]} sent to the district.{reward[1]}"), "irrigation_report", report.id)


def grievance(db: Session, user: FieldUser, steps: list[str]) -> UssdResult:
    title = ("Hitamo icyiciro:", "Choose a category:")
    outcome = paged_pick(title, grievance_options(db), steps)
    if outcome[0] == "screen":
        return outcome[1]
    if outcome[0] == "invalid":
        return end(INVALID)
    _, category, steps = outcome
    if not steps:
        return con(("Andika ikibazo cyawe. Izina ryawe ntirizagaragazwa.", "Type your concern. Your name will not be shown."))
    message = "*".join(steps).strip()
    if len(message) < 5:
        return end(INVALID)
    # Anonymised grievance log: keep the cell (for closing-the-loop SMS) but not the reporter.
    feedback = CommunityFeedback(reporter_id=None, cell_id=user.cell_id, scheme_id=scheme_for_cell(db, user.cell_id),
                                 category=category[1], message=message[:3000])
    db.add(feedback)
    db.flush()
    return end((f"Murakoze. Ikibazo cyawe FB-{feedback.id:03d} cyakiriwe. Tuzabamenyesha igisubizo.",
                f"Thank you. Your concern FB-{feedback.id:03d} was received. We will tell you the outcome."), "community_feedback", feedback.id)


def nutrition(db: Session, user: FieldUser, steps: list[str]) -> UssdResult:
    if not steps:
        return con(menu(("Ejo urugo rwanyu rwariye kangahe?", "How many meals did your household eat yesterday?"), MEALS))
    meals = pick(MEALS, steps[0])
    if not meals:
        return end(INVALID)
    if len(steps) == 1:
        return con(menu(("Muri iki cyumweru abana bariye inyama, amagi, amata cyangwa imboga?", "This week, did children eat meat, eggs, milk or vegetables?"), YES_NO))
    varied = pick(YES_NO, steps[1])
    if not varied:
        return end(INVALID)
    if len(steps) == 2:
        return con(menu(("Mufite ibiryo bihagije kugeza ku isarura?", "Do you have enough food until the next harvest?"), YES_NO))
    enough = pick(YES_NO, steps[2])
    if not enough:
        return end(INVALID)
    meals_per_day = int(steps[0])
    varied_diet, sufficient = varied[1] == "Yes", enough[1] == "Yes"
    survey = NutritionSurvey(reporter_id=user.id, cell_id=user.cell_id, meals_per_day=meals_per_day, ate_protein_or_vegetables=varied_diet,
                             food_sufficient=sufficient, stunting_risk_score=nutrition_risk_score(meals_per_day, varied_diet, sufficient))
    db.add(survey)
    db.flush()
    # Nutrition surveys are incentivised (Module 1): the reward reply mirrors the rainfall flow.
    reward = reward_line(db, user, from_nutrition_survey=True)
    return end((f"Murakoze! Ibisubizo byanyu bizafasha akarere kurwanya igwingira.{reward[0]}",
                f"Thank you! Your answers help the district fight stunting.{reward[1]}"), "nutrition_survey", survey.id)
