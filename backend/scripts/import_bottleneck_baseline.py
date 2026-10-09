"""Import historical AfDB evaluation findings as the bottleneck baseline (WP7, Section 9.3).

CSV columns: scheme, asset, category, date, description (an optional source column
is also read). Rows without a source are refused unless --source supplies one for
the whole file, because every calibration value must record where it came from:

    python scripts/import_bottleneck_baseline.py findings.csv \\
        --source "AfDB PADAB evaluation 2023" --apply

The imported findings ground the recurring-bottleneck rule: a category on a scheme
is only auto-flagged above its historical baseline, and the scheme page shows
"above historical baseline" next to it.

Exit codes: 0 = every row imported (or would be), 1 = at least one row refused.
"""
import argparse
import csv
import io
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make the `app` package importable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BottleneckBaseline, IrrigationScheme
from app.db.session import SessionLocal

COLUMNS = {
    "scheme": ("scheme", "name", "irrigation_scheme"),
    "asset": ("asset", "asset_name", "infrastructure"),
    "category": ("category", "bottleneck_category"),
    "date": ("date", "finding_date", "day"),
    "description": ("description", "finding", "details"),
    "source": ("source", "source_document", "document"),
}
KNOWN_CATEGORIES = {"technical", "social", "institutional", "environmental"}


def _field(row: dict, key: str) -> str:
    aliases = {alias.replace("_", " ") for alias in COLUMNS[key]}
    for candidate in row:
        if candidate.strip().lower().replace("_", " ") in aliases:
            return (row[candidate] or "").strip()
    return ""


def parse_findings(text: str, default_source: str = "") -> tuple[list[dict], list[str]]:
    """CSV text -> (rows, errors). Every row must end up with a source."""
    rows: list[dict] = []
    errors: list[str] = []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], ["The CSV has no header row."]
    for number, raw in enumerate(reader, start=2):
        scheme = _field(raw, "scheme")
        category = _field(raw, "category").lower()
        source = _field(raw, "source") or default_source
        if not scheme and not category and not _field(raw, "description"):
            continue  # blank line
        if not source:
            errors.append(f"row {number} ({scheme or 'unnamed'}): refused, no source (use the source column or --source)")
            continue
        if not scheme:
            errors.append(f"row {number}: refused, no scheme")
            continue
        if not category:
            errors.append(f"row {number} ({scheme}): refused, no category")
            continue
        raw_date = _field(raw, "date")
        finding_date = None
        if raw_date:
            try:
                finding_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
            except ValueError:
                errors.append(f"row {number} ({scheme}): refused, date must look like 2023-05-01")
                continue
        rows.append({
            "scheme": scheme, "asset_name": _field(raw, "asset") or None, "category": category,
            "finding_date": finding_date, "description": _field(raw, "description") or None, "source": source,
        })
    return rows, errors


def plan(db: Session, rows: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    """Match rows to schemes and drop exact duplicates: (matched, skipped_duplicates, errors)."""
    schemes = {scheme.name.lower(): scheme for scheme in db.scalars(select(IrrigationScheme))}
    existing = {
        (finding.scheme_id, finding.asset_name, finding.category, finding.finding_date, finding.description)
        for finding in db.scalars(select(BottleneckBaseline))
    }
    matched, duplicates, errors = [], [], []
    for row in rows:
        scheme = schemes.get(row["scheme"].lower())
        if scheme is None:
            errors.append(f"{row['scheme']}: no irrigation scheme with this name")
            continue
        key = (scheme.id, row["asset_name"], row["category"], row["finding_date"], row["description"])
        if key in existing:
            duplicates.append(row)
            continue
        existing.add(key)
        matched.append({**row, "scheme_id": scheme.id})
    return matched, duplicates, errors


def apply(db: Session, matched: list[dict]) -> None:
    for row in matched:
        db.add(BottleneckBaseline(
            scheme_id=row["scheme_id"], asset_name=row["asset_name"], category=row["category"],
            finding_date=row["finding_date"], description=row["description"], source=row["source"],
        ))
    db.commit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path", help="CSV file with scheme, asset, category, date, description")
    parser.add_argument("--source", default="", help="source document for rows that have no source column")
    parser.add_argument("--apply", action="store_true", help="write to the database (default: print only)")
    args = parser.parse_args(argv)

    path = Path(args.csv_path)
    if not path.is_file():
        print(f"ERROR: {path} does not exist.")
        return 1
    rows, errors = parse_findings(path.read_text(encoding="utf-8-sig"), args.source)

    db = SessionLocal()
    try:
        matched, duplicates, plan_errors = plan(db, rows)
        errors += plan_errors
        for row in matched:
            print(f"  {row['scheme']}: {row['category']}"
                  + (f" on {row['asset_name']}" if row["asset_name"] else "")
                  + (f" ({row['finding_date']})" if row["finding_date"] else "")
                  + f"  (source: {row['source']})")
            if row["category"] not in KNOWN_CATEGORIES:
                print(f"  note: '{row['category']}' is not one of the four USSD bottleneck categories; it will never be flagged")
        for message in errors:
            print(f"REFUSED {message}")
        if duplicates:
            print(f"Already imported (skipped): {len(duplicates)}")
        if errors:
            print("Nothing was written.")
            return 1
        if not matched:
            print("Nothing to import.")
            return 0
        if args.apply:
            apply(db, matched)
            print(f"Imported {len(matched)} baseline finding(s).")
        else:
            print(f"Would import {len(matched)} baseline finding(s). Re-run with --apply to save.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
