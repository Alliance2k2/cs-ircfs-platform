"""Idempotently add the two named pilot schemes with their published figures only.

PADAB: AfDB-funded, Mwesa Valley, 650 ha, two pumping stations, 65.5 km of canals.
APEFA Solar: solar-powered irrigation in Ngeruka and Mareba sectors.
Feasibility-study yield targets are NOT invented here; enter them in Platform Management
with their source once the official documents are confirmed. Existing values are never overwritten.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make the `app` package importable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import IrrigationScheme, Sector
from app.db.session import SessionLocal

PUBLISHED_FIGURES = {
    "PADAB": {"implementing_partner": "AfDB", "hectares_developed": 650.0, "sector": None},
    "APEFA Solar": {"implementing_partner": "APEFA", "hectares_developed": None, "sector": "Ngeruka"},
}


def seed_reference_schemes(db: Session) -> list[str]:
    changed: list[str] = []
    for name, figures in PUBLISHED_FIGURES.items():
        scheme = db.scalar(select(IrrigationScheme).where(func.lower(IrrigationScheme.name) == name.lower()))
        if scheme is None:
            scheme = IrrigationScheme(name=name, is_active=False)
            db.add(scheme)
            changed.append(f"{name} (added)")
        if scheme.implementing_partner is None:
            scheme.implementing_partner = figures["implementing_partner"]
        if scheme.hectares_developed is None and figures["hectares_developed"] is not None:
            scheme.hectares_developed = figures["hectares_developed"]
            changed.append(f"{name} area")
        if scheme.sector_id is None and figures["sector"]:
            scheme.sector_id = db.scalar(select(Sector.id).where(func.lower(Sector.name) == figures["sector"].lower()))
    db.commit()
    return changed


def main() -> None:
    with SessionLocal() as db:
        changed = seed_reference_schemes(db)
    print("Reference schemes updated:", ", ".join(changed) if changed else "none; already present")
    print("Yield targets, boundaries, and operational status were not inferred.")


if __name__ == "__main__":
    main()
