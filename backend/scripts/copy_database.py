"""Copy every platform table from one database to another (for example local PostgreSQL to Neon).

Both databases must already be at the same Alembic revision: run ``alembic upgrade head``
against the target first. Only the platform's own tables are copied (not PostGIS system
tables or GIS import leftovers). The copy runs in one transaction on the target, so it
either completes or changes nothing.

Usage (from backend/):
    python scripts/copy_database.py --target "<target DATABASE_URL>"            # source = DATABASE_URL in .env
    python scripts/copy_database.py --source "<url>" --target "<url>" --replace  # overwrite rows already in the target
"""
import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings, get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
import app.db.models  # noqa: E402,F401 - loads every table into Base.metadata

BATCH = 500


def normalise(url: str) -> str:
    return Settings(_env_file=None, database_url=url).database_url


def revision(connection) -> str | None:
    return connection.execute(text("SELECT version_num FROM alembic_version")).scalar()


def where(url: str) -> str:
    return url.rsplit("@", 1)[-1].split("?", 1)[0]  # host/database only, never the password


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=None, help="source DATABASE_URL (default: the one in .env)")
    parser.add_argument("--target", required=True, help="target DATABASE_URL")
    parser.add_argument("--replace", action="store_true", help="delete rows already in the target tables first")
    args = parser.parse_args()

    source_url = normalise(args.source) if args.source else get_settings().database_url
    target_url = normalise(args.target)
    if source_url == target_url:
        print("Source and target are the same database.")
        return 1
    source, target = create_engine(source_url), create_engine(target_url)
    tables = Base.metadata.sorted_tables

    with source.connect() as src, target.begin() as dst:
        if revision(src) != revision(dst):
            print(f"Revisions differ (source {revision(src)}, target {revision(dst)}). Run `alembic upgrade head` on both first.")
            return 1
        occupied = [table.name for table in tables if dst.execute(select(func.count()).select_from(table)).scalar()]
        if occupied and not args.replace:
            print(f"The target already has rows in: {', '.join(occupied)}. Re-run with --replace to overwrite them.")
            return 1
        print(f"Copying {where(source_url)} -> {where(target_url)} at revision {revision(src)}")
        source_columns = {name: {c["name"] for c in inspect(src).get_columns(name)} for name in inspect(src).get_table_names()}
        target_columns = {name: {c["name"] for c in inspect(dst).get_columns(name)} for name in inspect(dst).get_table_names()}

        for table in reversed(tables):
            dst.execute(table.delete())
        totals = {}
        for table in tables:
            shared = [column for column in table.columns
                      if column.name in source_columns.get(table.name, set()) & target_columns.get(table.name, set())]
            skipped = {column.name for column in table.columns} - {column.name for column in shared}
            if skipped:
                print(f"  {table.name}: columns not in both databases, left empty: {', '.join(sorted(skipped))}")
            rows = [dict(row._mapping) for row in src.execute(select(*shared))]
            for start in range(0, len(rows), BATCH):
                dst.execute(table.insert(), rows[start:start + BATCH])
            totals[table.name] = len(rows)
            # Keep new IDs after the copied ones.
            if "id" in table.columns and target.dialect.name == "postgresql":
                dst.execute(text(f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                                 f"COALESCE((SELECT MAX(id) FROM {table.name}), 0) + 1, false)"))
        for table in tables:
            copied = dst.execute(select(func.count()).select_from(table)).scalar()
            if copied != totals[table.name]:
                raise RuntimeError(f"{table.name}: copied {copied} of {totals[table.name]} rows")

    for name, count in totals.items():
        if count:
            print(f"  {name}: {count}")
    print(f"Done: {sum(totals.values())} rows in {sum(1 for c in totals.values() if c)} tables, verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
