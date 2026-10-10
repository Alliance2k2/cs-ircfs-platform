"""Compare the database at DATABASE_URL with the ORM models and list every difference.

Exit code 1 when they differ. Used by CI after `alembic upgrade head` on a clean
PostGIS database, and useful before a deployment:

    python scripts/check_schema.py
"""
import sys
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
import app.db.models  # noqa: E402,F401 - loads every table

# PostGIS's own tables and views are not part of the platform schema.
SYSTEM_TABLES = {"spatial_ref_sys", "geography_columns", "geometry_columns"}


def differences(url: str) -> list:
    engine = create_engine(url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={
            "compare_type": True,
            "include_name": lambda name, kind, _parent: not (kind == "table" and name in SYSTEM_TABLES),
        })
        return compare_metadata(context, Base.metadata)


def main() -> int:
    diffs = differences(get_settings().database_url)
    for diff in diffs:
        print(repr(diff)[:300])
    print(f"{len(diffs)} difference(s) between the database and the models.")
    return 1 if diffs else 0


if __name__ == "__main__":
    raise SystemExit(main())
