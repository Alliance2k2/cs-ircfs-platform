"""Import verified yield targets for irrigation schemes (WP7, Section 9.1).

Reads a CSV with one row per scheme and records where every figure came from:

    scheme,yield_target_tons,hectares,source_document,source_page
    PADAB,4120,650,Feasibility study 2023,17
    APEFA Solar,1150,120,APEFA commissioning report,4

Rows without a source document are refused: no target is ever saved without one.
Nothing is written unless --apply is given; without it the script only prints
what it would do. The manual route is Platform Management on schemes.html.

Exit codes: 0 = every row imported (or would be), 1 = at least one row refused.
"""
import argparse
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make the `app` package importable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import IrrigationScheme
from app.db.session import SessionLocal

# Header aliases tolerated in the CSV (lower-cased, spaces stripped).
COLUMNS = {
    "scheme": ("scheme", "name", "irrigation_scheme"),
    "yield_target_tons": ("yield_target_tons", "yield_target", "target_tons", "yield tons"),
    "hectares": ("hectares", "hectares_developed", "ha"),
    "source_document": ("source_document", "source", "document"),
    "source_page": ("source_page", "page"),
}


def _field(row: dict, key: str) -> str:
    aliases = {alias.replace("_", " ") for alias in COLUMNS[key]}
    for candidate in row:
        if candidate.strip().lower().replace("_", " ") in aliases:
            return (row[candidate] or "").strip()
    return ""


def parse_targets(text: str) -> tuple[list[dict], list[str]]:
    """CSV text -> (rows, errors). Every row must carry a source document."""
    rows: list[dict] = []
    errors: list[str] = []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], ["The CSV has no header row."]
    for number, raw in enumerate(reader, start=2):  # row 1 is the header
        scheme = _field(raw, "scheme")
        target = _field(raw, "yield_target_tons").replace(",", ".")
        source = _field(raw, "source_document")
        page = _field(raw, "source_page")
        if not scheme and not target and not source:
            continue  # blank line
        if not source:
            errors.append(f"row {number} ({scheme or 'unnamed'}): refused, no source document")
            continue
        try:
            tons = float(target)
        except ValueError:
            errors.append(f"row {number} ({scheme}): refused, yield target is not a number")
            continue
        if tons <= 0:
            errors.append(f"row {number} ({scheme}): refused, yield target must be positive")
            continue
        hectares_text = _field(raw, "hectares").replace(",", ".")
        try:
            hectares = float(hectares_text) if hectares_text else None
        except ValueError:
            errors.append(f"row {number} ({scheme}): refused, hectares is not a number")
            continue
        rows.append({
            "scheme": scheme,
            "yield_target_tons": tons,
            "hectares": hectares,
            "source": f"{source}, p.{page}" if page else source,
        })
    return rows, errors


def plan(db: Session, rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Match rows to schemes in the database; returns (matched, errors)."""
    schemes = {scheme.name.lower(): scheme for scheme in db.scalars(select(IrrigationScheme))}
    matched, errors = [], []
    for row in rows:
        scheme = schemes.get(row["scheme"].lower())
        if scheme is None:
            errors.append(f"{row['scheme']}: no irrigation scheme with this name")
            continue
        matched.append({**row, "scheme_id": scheme.id, "current_target": scheme.baseline_yield_target_tons})
    return matched, errors


def apply(db: Session, matched: list[dict]) -> None:
    for row in matched:
        scheme = db.get(IrrigationScheme, row["scheme_id"])
        scheme.baseline_yield_target_tons = row["yield_target_tons"]
        scheme.baseline_source = row["source"]
        if row["hectares"] is not None:
            scheme.hectares_developed = row["hectares"]
    db.commit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path", help="CSV file with scheme, yield_target_tons, hectares, source_document, source_page")
    parser.add_argument("--apply", action="store_true", help="write to the database (default: print only)")
    args = parser.parse_args(argv)

    path = Path(args.csv_path)
    if not path.is_file():
        print(f"ERROR: {path} does not exist.")
        return 1
    rows, errors = parse_targets(path.read_text(encoding="utf-8-sig"))

    db = SessionLocal()
    try:
        matched, plan_errors = plan(db, rows)
        errors += plan_errors
        for row in matched:
            action = "update" if row["current_target"] is not None else "set"
            print(f"  {row['scheme']}: {action} target {row['yield_target_tons']} t"
                  + (f", {row['hectares']} ha" if row["hectares"] is not None else "")
                  + f"  (source: {row['source']})")
        if errors:
            for message in errors:
                print(f"REFUSED {message}")
            print("Nothing was written.")
            return 1
        if not matched:
            print("Nothing to import: the CSV has no rows.")
            return 0
        if args.apply:
            apply(db, matched)
            print(f"Imported {len(matched)} scheme target(s).")
        else:
            print(f"Would import {len(matched)} scheme target(s). Re-run with --apply to save.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
