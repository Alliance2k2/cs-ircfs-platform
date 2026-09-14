"""Idempotently add the two named pilot schemes without unverified metrics."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import IrrigationScheme
from app.db.session import SessionLocal


REFERENCE_SCHEMES = ("PADAB", "APEFA Solar")


def seed_reference_schemes(db: Session) -> list[str]:
    created: list[str] = []
    for name in REFERENCE_SCHEMES:
        exists = db.scalar(select(IrrigationScheme.id).where(func.lower(IrrigationScheme.name) == name.lower()))
        if exists is None:
            db.add(IrrigationScheme(name=name, is_active=False))
            created.append(name)
    db.commit()
    return created


def main() -> None:
    with SessionLocal() as db:
        created = seed_reference_schemes(db)
    print("Added reference schemes:", ", ".join(created) if created else "none; already present")
    print("No hectares, targets, boundaries, or operational status were inferred.")


if __name__ == "__main__":
    main()
