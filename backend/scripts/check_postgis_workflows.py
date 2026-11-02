"""Validate pilot services in a disposable local PostGIS database; all fixtures roll back.

Set POSTGIS_VALIDATION_URL to a localhost database ending in '_validation', migrated
to head. This deliberately refuses the application's configured DATABASE_URL.
"""
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import Principal
from app.db.models import (AssetMaintenance, AssetOutage, Cell, CitizenScienceLog, IrrigationClimateLog,
                           IrrigationScheme, RainfallReference, SchemeAsset, SchemeBaseline, Sector, UserRole)
from app.services.climate import rainfall_analysis
from app.services.maintenance import maintenance_history
from app.services.yield_evaluation import evaluate_yield


def main():
    value = os.environ.get("POSTGIS_VALIDATION_URL", "")
    if not value:
        raise SystemExit("Set POSTGIS_VALIDATION_URL explicitly; DATABASE_URL is never used here")
    url = make_url(value)
    if url.get_backend_name() != "postgresql" or url.host not in ("127.0.0.1", "localhost") or not (url.database or "").endswith("_validation"):
        raise SystemExit("Refusing a database that is not an explicitly named local *_validation database")
    engine = create_engine(url)
    with engine.connect() as connection:
        transaction = connection.begin()
        db = Session(bind=connection)
        try:
            print("PostgreSQL", connection.scalar(text("SHOW server_version")))
            print("PostGIS", connection.scalar(text("SELECT PostGIS_Lib_Version()")))
            assert connection.scalar(text("SELECT ST_AsText(ST_GeomFromText('POINT(0 0)', 4326))")) == "POINT(0 0)"
            marker = "VALIDATION-" + uuid4().hex
            sector = Sector(name=marker)
            db.add(sector)
            db.flush()
            cell = Cell(name=marker, sector_id=sector.id)
            scheme = IrrigationScheme(name=marker, sector_id=sector.id)
            db.add_all([cell, scheme])
            db.flush()
            asset = SchemeAsset(name_en=marker, name_rw=marker, scheme_id=scheme.id, cell_id=cell.id)
            db.add(asset)
            db.flush()
            # Execute the row-lock shape used by outage writes on the real PostgreSQL dialect.
            db.scalar(select(SchemeAsset).where(SchemeAsset.id == asset.id).with_for_update())
            db.add(SchemeBaseline(scheme_id=scheme.id, crop_type="Rice", season="A", reference_year=2026,
                expected_yield=4000, yield_unit="kg/ha", official_source="Synthetic validation fixture", document_reference="fixture",
                data_origin="import", verification_status="verified", approved_at=date(2026, 9, 1)))
            db.add(CitizenScienceLog(scheme_id=scheme.id, cell_id=cell.id, crop_type="Rice", season="A", reference_year=2026,
                reported_harvest_tons=6, harvested_area_hectares=2, observation_type="measured", data_source="Synthetic fixture",
                verification_status="verified", harvest_date=date(2026, 10, 1)))
            for day, mm in ((date(2026, 10, 1), 10), (date(2026, 10, 2), 20)):
                db.add(IrrigationClimateLog(scheme_id=scheme.id, cell_id=cell.id, rainfall_mm=mm, observation_date=day,
                    gauge_code=marker, data_source="Synthetic validation fixture", verification_status="verified"))
            ref = RainfallReference(sector_id=sector.id, period_start=date(2026, 10, 1), period_end=date(2026, 10, 2),
                reference_start_year=1991, reference_end_year=2020, mean_rainfall_mm=20, source="Synthetic validation fixture",
                document_reference="fixture", approved_at=date(2026, 9, 1))
            outage = AssetOutage(asset_id=asset.id, cell_id=cell.id, started_at=datetime(2026, 10, 1, 6, tzinfo=timezone.utc),
                ended_at=datetime(2026, 10, 1, 12, tzinfo=timezone.utc), category="technical", description="Synthetic fixture",
                source="Synthetic validation fixture", repair_status="repaired")
            db.add_all([ref, outage])
            db.flush()
            db.add(AssetMaintenance(asset_id=asset.id, cell_id=cell.id, outage_id=outage.id, performed_at=outage.ended_at,
                kind="repair", action="Synthetic test repair", source="Synthetic validation fixture", restored=True))
            db.flush()
            principal = Principal(name="validation", role=UserRole.administrator)
            assert evaluate_yield(db, scheme.id)["value"] == 75
            result = rainfall_analysis(db, principal, date(2026, 10, 1), date(2026, 10, 2), sector_id=sector.id, reference_id=ref.id)
            assert result["anomaly"]["percent"] == 50
            result = maintenance_history(db, principal, date(2026, 10, 1), date(2026, 10, 2), asset_id=asset.id)
            assert result["assets"][0]["recorded_downtime_hours"] == 6
            assert result["assets"][0]["maintenance"][0]["restored"] is True
            print("PASS: spatial round trip, row-lock query, yield=75%, rainfall anomaly=50%, recorded downtime=6h")
        finally:
            db.close()
            if transaction.is_active:
                transaction.rollback()
    engine.dispose()
    print("Synthetic workflow fixtures rolled back; no application database used")


if __name__ == "__main__":
    main()
