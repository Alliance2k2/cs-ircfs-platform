from datetime import datetime,timedelta,timezone
from app.db.models import Cell,Sector,IrrigationClimateLog
from app.services.climate import KIGALI
from app.services.reporting import build_monthly_report,build_trends
from app.services.analytics import rainfall_map
from app.services.advisory import rainfall_by_sector


def test_rainfall_views_use_latest_observation_and_preserve_measured_zero(db):
    sector=Sector(name="Test sector")
    db.add(sector);db.flush()
    cell=Cell(name="Test cell",sector_id=sector.id,latitude=-2,longitude=30)
    db.add(cell);db.flush()
    now=datetime.now(timezone.utc);today=now.astimezone(KIGALI).date()
    for gauge,day,mm,offset in [('A',today-timedelta(days=1),999,-3),('A',today-timedelta(days=1),10,-2),('B',today-timedelta(days=1),30,-1),('A',today,0,0)]:
        db.add(IrrigationClimateLog(cell_id=cell.id,gauge_code=gauge,observation_date=day,rainfall_mm=mm,
            data_source="District test sheet",verification_status="verified",created_at=now+timedelta(seconds=offset)))
    db.commit()
    assert rainfall_by_sector(db)[sector.id]==(20,3)
    assert rainfall_map(db)[0]["rainfall_mm"]==20
    month=build_monthly_report(db,today.strftime('%Y-%m'))
    # At a month boundary, only today's measured zero belongs in this month.
    expected=0 if today.day==1 else 20
    assert month["rainfall"][0]["rainfall_mm"]==expected
    assert build_trends(db,2)["months"][-1]["rainfall_mm"]==expected


def test_late_old_reading_is_not_assigned_to_receipt_month_or_recent_map(db):
    sector=Sector(name="Test sector")
    db.add(sector);db.flush()
    cell=Cell(name="Test cell",sector_id=sector.id,latitude=-2,longitude=30)
    db.add(cell);db.flush()
    now=datetime.now(timezone.utc);observed=now.astimezone(KIGALI).date()-timedelta(days=65)
    db.add(IrrigationClimateLog(cell_id=cell.id,gauge_code="A",observation_date=observed,rainfall_mm=12,created_at=now))
    db.commit()
    assert rainfall_map(db)[0]["rainfall_mm"] is None
    assert build_monthly_report(db,observed.strftime('%Y-%m'))["rainfall"][0]["rainfall_mm"]==12
    assert build_trends(db,4)["months"][-1]["rainfall_mm"] is None
