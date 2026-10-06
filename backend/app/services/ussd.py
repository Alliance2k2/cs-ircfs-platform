"""Kinyarwanda-first USSD menu for *801# (architecture Sections 4 and 8.4).

Africa's Talking calls the callback once per keypress with the full answer path in
``text`` (for example ``"3*12"``), and expects a reply beginning with ``CON`` (show
another screen) or ``END`` (close the session). The menu is therefore stateless: the
path is replayed on every request.

Design rules from the architecture: numeric answers wherever possible, no free text
except the grievance message, and at most three levels below the main menu.
"""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.db.models import CommunityFeedback, NutritionSurvey, User
from app.services.advisory import local_tip, maybe_reward, nutrition_risk_score
from app.services.reporting import create_crop_report, create_irrigation_report, scheme_by_prefix, scheme_for_cell

# (Kinyarwanda, English) pairs. Kinyarwanda wording should be reviewed with field teams.
MAIN = ("Kaze kuri CS-IRCFS. Hitamo:\n1. Rapora umusaruro\n2. Indwara/udukoko\n3. Rapora imvura\n4. Ibikorwa remezo byo kuhira\n5. Tanga ikibazo/igitekerezo\n6. Imirire y'urugo",
        "Welcome to CS-IRCFS. Choose:\n1. Report harvest\n2. Disease/pests\n3. Report rainfall\n4. Irrigation infrastructure\n5. Submit a grievance/feedback\n6. Household nutrition")

CROPS = [("Umuceri", "Rice"), ("Ibigori", "Maize"), ("Ibishyimbo", "Beans"), ("Imyumbati", "Cassava"), ("Imboga", "Vegetables")]
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


def pick(options: list, answer: str):
    """Return the chosen option for a 1-based numeric answer, or None."""
    return options[int(answer) - 1] if answer.isdigit() and 1 <= int(answer) <= len(options) else None


def number(answer: str, low: float, high: float) -> float | None:
    try:
        value = float(answer.replace(",", "."))
    except ValueError:
        return None
    return value if low <= value <= high else None


def con(screen: tuple[str, str]) -> UssdResult:
    return UssdResult("CON " + screen[0], screen[1])


def end(screen: tuple[str, str], record_type: str | None = None, record_id: int | None = None) -> UssdResult:
    return UssdResult("END " + screen[0], screen[1], record_type, record_id)


def handle(db: Session, user: User, text: str) -> UssdResult:
    """Route one USSD request. The caller commits the transaction."""
    steps = [step.strip() for step in text.split("*")] if text else []
    if not steps:
        return con(MAIN)
    flows = {"1": harvest, "2": pest, "3": rainfall, "4": infrastructure, "5": grievance, "6": nutrition}
    flow = flows.get(steps[0])
    return flow(db, user, steps[1:]) if flow else end(INVALID)


def harvest(db: Session, user: User, steps: list[str]) -> UssdResult:
    if not steps:
        return con(menu(("Hitamo igihingwa:", "Choose the crop:"), CROPS))
    crop = pick(CROPS, steps[0])
    if not crop:
        return end(INVALID)
    if len(steps) == 1:
        return con((f"{crop[0]}: andika umusaruro uteganyijwe (toni), urugero 2.5", f"{crop[1]}: enter the expected harvest (tons), e.g. 2.5"))
    tons = number(steps[1], 0, 999)
    if tons is None:
        return end(INVALID)
    report = create_crop_report(db, reporter_id=user.id, cell_id=user.cell_id, scheme_id=scheme_for_cell(db, user.cell_id),
                                crop_type=crop[1], expected_harvest_tons=tons, notes="Submitted by USSD")
    tip = local_tip(db, user)
    return end((f"Murakoze! Umusaruro wa {crop[0]} ({tons} t) wanditswe. Nimero #{report.id}.\n{tip}",
                f"Thank you! {crop[1]} harvest ({tons} t) recorded as #{report.id}.\n(Local tip sent in Kinyarwanda.)"), "crop_report", report.id)


def pest(db: Session, user: User, steps: list[str]) -> UssdResult:
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


def reward_line(db: Session, user: User) -> tuple[str, str]:
    reward = maybe_reward(db, user)
    if not reward:
        return "", ""
    return f"\nWahawe {reward.amount_rwf} RWF y'itumanaho. Murakoze!", f"\nYou earned {reward.amount_rwf} RWF airtime."


def rainfall(db: Session, user: User, steps: list[str]) -> UssdResult:
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


def infrastructure(db: Session, user: User, steps: list[str]) -> UssdResult:
    if not steps:
        return con(menu(("Hitamo igikorwa remezo:", "Choose the asset:"), ASSETS))
    asset = pick(ASSETS, steps[0])
    if not asset:
        return end(INVALID)
    if len(steps) == 1:
        return con(menu(("Imiterere yacyo:", "Its condition:"), STATUS))
    status = pick(STATUS, steps[1])
    if not status:
        return end(INVALID)
    if status[2] != "operational" and len(steps) == 2:
        return con(menu(("Impamvu nyamukuru:", "Main cause:"), BOTTLENECKS))
    bottleneck = pick(BOTTLENECKS, steps[2]) if status[2] != "operational" else None
    if status[2] != "operational" and not bottleneck:
        return end(INVALID)
    report = create_irrigation_report(db, reporter_id=user.id, cell_id=user.cell_id, scheme_id=scheme_by_prefix(db, asset[2]),
                                      infrastructure_name=asset[1], operational_status=status[2],
                                      bottleneck_category=bottleneck[2] if bottleneck else None,
                                      fault_description=f"USSD report: {status[1]}" + (f", {bottleneck[1]}" if bottleneck else ""))
    reward = reward_line(db, user)
    if status[2] == "operational":
        return end((f"Murakoze! {asset[0]} yanditswe ko ikora neza.{reward[0]}", f"Thank you! {asset[1]} recorded as working.{reward[1]}"), "irrigation_report", report.id)
    return end((f"Murakoze! Ikibazo #{report.id} cya {asset[0]} cyoherejwe ku karere.{reward[0]}",
                f"Thank you! Fault #{report.id} on {asset[1]} sent to the district.{reward[1]}"), "irrigation_report", report.id)


def grievance(db: Session, user: User, steps: list[str]) -> UssdResult:
    if not steps:
        return con(menu(("Hitamo icyiciro:", "Choose a category:"), GRIEVANCES))
    category = pick(GRIEVANCES, steps[0])
    if not category:
        return end(INVALID)
    if len(steps) == 1:
        return con(("Andika ikibazo cyawe. Izina ryawe ntirizagaragazwa.", "Type your concern. Your name will not be shown."))
    message = "*".join(steps[1:]).strip()
    if len(message) < 5:
        return end(INVALID)
    # Anonymised grievance log: keep the cell (for closing-the-loop SMS) but not the reporter.
    feedback = CommunityFeedback(reporter_id=None, cell_id=user.cell_id, scheme_id=scheme_for_cell(db, user.cell_id),
                                 category=category[1], message=message[:3000])
    db.add(feedback)
    db.flush()
    return end((f"Murakoze. Ikibazo cyawe FB-{feedback.id:03d} cyakiriwe. Tuzabamenyesha igisubizo.",
                f"Thank you. Your concern FB-{feedback.id:03d} was received. We will tell you the outcome."), "community_feedback", feedback.id)


def nutrition(db: Session, user: User, steps: list[str]) -> UssdResult:
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
    return end(("Murakoze! Ibisubizo byanyu bizafasha akarere kurwanya igwingira.", "Thank you! Your answers help the district fight stunting."), "nutrition_survey", survey.id)
