"""Fill a DEMONSTRATION database with a realistic month of pilot activity.

Use it for evaluation and training, never on the real pilot database. All people,
cooperatives, and yield targets are invented and labelled as demonstration values.

    start-local.ps1 -Demo            # recommended: separate demo.db, seeded automatically
    python scripts/seed_demo_data.py # on the configured database (asks for confirmation unless SQLite)
"""
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make the `app` package importable

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.models import (Cell, CommunityFeedback, FeedbackStatusEvent, IncidentCase, IncidentEvent, InboundMessage,  # noqa: E402
                           IrrigationScheme, NutritionSurvey, ReportStatus, Sector, FieldUser, UserRole)
from app.db.session import SessionLocal  # noqa: E402
from app.services.advisory import maybe_reward, nutrition_risk_score  # noqa: E402
from app.services.reporting import create_crop_report, create_irrigation_report  # noqa: E402
from load_locations import load as load_locations  # noqa: E402
from seed_reference_schemes import seed_reference_schemes  # noqa: E402

DEMO_PREFIX = "+2507885500"
DEMO_TARGET_SOURCE = "DEMONSTRATION VALUE - replace with the feasibility-study figure"
NOW = datetime.now(timezone.utc)
COOPERATIVES = [  # (cooperative, sector, scheme prefix, typical rainfall mm/day)
    ("Demo Koperative Twitezimbere", "Ngeruka", "APEFA", 0.9),
    ("Demo Koperative Dukorere Hamwe", "Mareba", "APEFA", 1.2),
    ("Demo Koperative Abahuzamugambi", "Nyamata", "PADAB", 3.4),
]
NAMES = ["Aline Umutoni", "Jean Habineza", "Claudine Mukamana", "Eric Niyonzima", "Diane Uwase", "Patrick Mugisha", "Grace Ingabire",
         "Emmanuel Nshimiyimana", "Josiane Mukeshimana", "Olivier Habimana", "Chantal Uwimana", "Innocent Ndayisaba", "Solange Iradukunda",
         "Fabrice Manzi", "Vestine Nyirahabimana", "Theogene Hakizimana", "Alice Mutoni", "Samuel Bizimana", "Claire Uwamahoro",
         "Jean Bosco Nkurunziza", "Beatrice Mukandayisenga", "Didier Twagirayezu", "Odette Nyiransabimana", "Pacifique Iradukunda"]
CROPS = ["Rice", "Maize", "Beans", "Cassava", "Vegetables"]
GRIEVANCES = [
    ("Water Pricing", "The irrigation water fee doubled this season without explanation."),
    ("Input Distribution", "Fertiliser arrived three weeks after planting for our group."),
    ("Resettlement/Downstream Impact", "Households moved for the dam have not received the promised plots."),
    ("Operational Challenge", "Canal gate near our plots is opened at night without notice."),
    ("Water Pricing", "Members cannot pay the water fee before harvest; please allow instalments."),
    ("Input Distribution", "Improved maize seed was not enough for all registered members."),
    ("Resettlement/Downstream Impact", "Downstream fields flood when the scheme releases water."),
    ("Operational Challenge", "No one answers when we report broken valves at the pumping station."),
]


def ago(days: float) -> datetime:
    return NOW - timedelta(days=days)


def seed(db: Session) -> str:
    if db.scalar(select(func.count()).select_from(FieldUser).where(FieldUser.phone_number.like(f"{DEMO_PREFIX}%"))):
        return "Demonstration data already present; nothing added."
    rng = random.Random(2026)
    if not db.scalar(select(func.count()).select_from(Cell)):
        load_locations(db)
    seed_reference_schemes(db)
    schemes = {name.split()[0]: scheme for name, scheme in ((s.name, s) for s in db.scalars(select(IrrigationScheme)))}
    for prefix, target in (("PADAB", 140.0), ("APEFA", 75.0)):
        scheme = schemes[prefix]
        scheme.is_active = True
        if scheme.baseline_yield_target_tons is None:
            scheme.baseline_yield_target_tons, scheme.baseline_source = target, DEMO_TARGET_SOURCE
    db.flush()

    users: list[tuple[FieldUser, str]] = []
    names = iter(NAMES)
    for coop_index, (coop, sector_name, scheme_prefix, _) in enumerate(COOPERATIVES):
        cells = list(db.scalars(select(Cell).join(Sector).where(Sector.name == sector_name).order_by(Cell.name)))
        for member in range(8):
            role = UserRole.cooperative_leader if member == 0 else UserRole.citizen_science_monitor if member in (1, 2) else UserRole.farmer
            user = FieldUser(phone_number=f"{DEMO_PREFIX}{coop_index}{member}", full_name=next(names), role=role, cooperative_name=coop,
                        cell_id=cells[member % len(cells)].id if cells else None, created_at=ago(40 - member))
            db.add(user)
            users.append((user, scheme_prefix))
    db.add(FieldUser(phone_number=f"{DEMO_PREFIX}99", full_name="Demo District Planner", role=UserRole.district_planner))
    db.flush()

    def stamp(record, days):
        record.created_at = ago(days)
        return record

    # Module 1: harvest forecasts, reported harvests, and pest/disease alerts.
    for user, prefix in users:
        for _ in range(2):
            crop = rng.choice(CROPS[:3])
            expected = round(rng.uniform(1.2, 4.5), 1)
            stamp(create_crop_report(db, reporter_id=user.id, cell_id=user.cell_id, scheme_id=schemes[prefix].id, crop_type=crop,
                                     planting_date=(NOW - timedelta(days=rng.randint(60, 110))).date(), expected_harvest_tons=expected,
                                     reported_harvest_tons=round(expected * rng.uniform(0.55, 1.05), 1) if rng.random() < 0.6 else None,
                                     notes="Demo: USSD harvest update"), rng.uniform(1, 30))
    pests = [("Fall armyworm", "Maize", 5), ("Fall armyworm", "Maize", 4), ("Fall armyworm", "Maize", 4), ("Leaf disease", "Beans", 3),
             ("Fall armyworm", "Maize", 3), ("Root disease", "Cassava", 4), ("Leaf disease", "Rice", 2), ("Fall armyworm", "Maize", 2)]
    for index, (pest, crop, severity) in enumerate(pests):
        user, prefix = users[(index * 3) % len(users)]
        stamp(create_crop_report(db, reporter_id=user.id, cell_id=user.cell_id, scheme_id=schemes[prefix].id, crop_type=crop,
                                 pest_or_disease=pest, severity=severity, notes="Demo: SMS keyword alert"), rng.uniform(0.2, 12))

    # Module 2: daily rain-gauge readings (dry in APEFA sectors, normal in Nyamata) and asset faults.
    monitors = [(user, prefix, COOPERATIVES[index // 8][3]) for index, (user, prefix) in enumerate(users) if user.role != UserRole.farmer]
    for user, prefix, typical in monitors:
        for day in range(7, 0, -1):
            stamp(create_irrigation_report(db, reporter_id=user.id, cell_id=user.cell_id, scheme_id=schemes[prefix].id,
                                           infrastructure_name="Citizen rain gauge", rainfall_mm=round(max(0, rng.gauss(typical, typical * 0.6)), 1)), day - 0.3)
            maybe_reward(db, user)
    faults = [("PADAB Pumping Station 1", "offline", "technical", "Motor overheats and trips after 20 minutes.", 9),
              ("PADAB Pumping Station 1", "faulty", "technical", "Pressure loss on the main delivery pipe.", 5),
              ("PADAB Pumping Station 1", "offline", "technical", "Pump stopped again; spare part not available.", 1),
              ("PADAB canal network (65.5 km)", "faulty", "environmental", "Siltation blocks secondary canal C4.", 6),
              ("PADAB canal network (65.5 km)", "faulty", "social", "Unauthorised diversion near the market road.", 3),
              ("APEFA solar pump - Mareba", "faulty", "technical", "Two solar panels cracked; output reduced.", 2),
              ("APEFA solar pump - Ngeruka", "operational", None, "Routine check: working well.", 1)]
    for name, status, category, description, days in faults:
        prefix = name.split()[0]
        operator = next(user for user, p, _ in monitors if p == prefix)
        stamp(create_irrigation_report(db, reporter_id=operator.id, cell_id=operator.cell_id, scheme_id=schemes[prefix].id, infrastructure_name=name,
                                       operational_status=status, bottleneck_category=category, fault_description=description), days)
    db.flush()
    for case in db.scalars(select(IncidentCase).order_by(IncidentCase.id).limit(3)):
        stamp(case, 8)
        db.add(stamp(IncidentEvent(case_id=case.id, previous_status=ReportStatus.open, new_status=ReportStatus.resolved, action_taken="Demo: technician repaired the fault"), 6))
        case.status, case.action_taken = ReportStatus.resolved, "Demo: technician repaired the fault"

    # Module 3: anonymous grievances, half of them resolved with an audit trail.
    for index, (category, message) in enumerate(GRIEVANCES):
        user, prefix = users[(index * 5 + 2) % len(users)]
        opened = rng.uniform(4, 25)
        feedback = stamp(CommunityFeedback(cell_id=user.cell_id, scheme_id=schemes[prefix].id, category=category, message=message), opened)
        db.add(feedback)
        db.flush()
        if index % 2:
            feedback.status, feedback.action_taken = ReportStatus.resolved, "Demo: cooperative meeting held and decision shared"
            db.add(stamp(FeedbackStatusEvent(feedback_id=feedback.id, previous_status=ReportStatus.open, new_status=ReportStatus.resolved,
                                             action_taken=feedback.action_taken), opened - rng.uniform(0.5, 3.5)))

    # Module 1: Household Nutrition Tracker.
    for user, _ in users:
        meals, varied, enough = rng.choice([1, 2, 2, 3, 3]), rng.random() < 0.55, rng.random() < 0.6
        db.add(stamp(NutritionSurvey(reporter_id=user.id, cell_id=user.cell_id, meals_per_day=meals, ate_protein_or_vegetables=varied,
                                     food_sufficient=enough, stunting_risk_score=nutrition_risk_score(meals, varied, enough)), rng.uniform(1, 20)))

    for text, reply, channel in (("2*2*1*5", "END Murakoze! Raporo ya Nzana yakiriwe.", "ussd"), ("NGERUKA NZANA 4", "Murakoze! Raporo ya Nzana yakiriwe.", "sms"),
                                 ("3*0.5", "END Murakoze! Imvura 0.5 mm yanditswe.", "ussd")):
        db.add(stamp(InboundMessage(phone_number=users[0][0].phone_number, channel=channel, text=text, reply=reply), 0.5))
    db.commit()
    return f"Demonstration data added: {len(users)} people in 3 cooperatives, reports for the last 30 days."


def main() -> None:
    with SessionLocal() as db:
        if db.bind.dialect.name != "sqlite" and "--yes" not in sys.argv:
            answer = input("This adds invented demonstration records to a non-SQLite database. Continue? [y/N] ")
            if answer.strip().lower() != "y":
                raise SystemExit("Cancelled.")
        print(seed(db))


if __name__ == "__main__":
    main()
