"""WP2: weekly automatic advice is idempotent, dry-run safe, and skips empty sectors."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.config import Settings
from app.db.models import (
    AdviceRun,
    AdvisoryMessage,
    Cell,
    FieldUser,
    IrrigationClimateLog,
    Sector,
    UserRole,
)
from app.services import advisory


def seed(db, readings: int = 1) -> Sector:
    """One sector with a monitor phone and rainfall readings so advice has data."""
    sector = Sector(name="Ngeruka", latitude=-2.35, longitude=30.15)
    db.add(sector)
    db.flush()
    cell = Cell(name="Gihembe", sector_id=sector.id, latitude=-2.34, longitude=30.16)
    db.add(cell)
    db.flush()
    db.add(FieldUser(phone_number="+250788000001", role=UserRole.citizen_science_monitor, cell_id=cell.id))
    for index in range(readings):
        db.add(IrrigationClimateLog(cell_id=cell.id, rainfall_mm=1.0 + index, reporter_id=None))
    db.commit()
    return sector


def test_weekly_advice_sends_once_per_week(db, monkeypatch):
    monkeypatch.setattr("app.services.forecast.get_settings", lambda: Settings(_env_file=None, weather_forecast_enabled=False))
    sector = seed(db)
    first = advisory.send_weekly_advice(db)
    assert first["sectors"] and first["total_recipients"] == 1
    assert first["week_key"] == advisory.current_week_key()
    second = advisory.send_weekly_advice(db)
    assert second["sectors"] == [] and second["skipped_already_sent"] == 1
    sent = db.scalar(select(func.count()).select_from(AdvisoryMessage).where(AdvisoryMessage.purpose == "irrigation_schedule"))
    assert sent == 1
    runs = db.scalars(select(AdviceRun).where(AdviceRun.sector_id == sector.id)).all()
    assert len(runs) == 1 and runs[0].week_key == advisory.current_week_key()


def test_weekly_advice_dry_run_records_without_sending(db, monkeypatch):
    monkeypatch.setattr("app.services.forecast.get_settings", lambda: Settings(_env_file=None, weather_forecast_enabled=False))
    seed(db)
    summary = advisory.send_weekly_advice(db)
    assert summary["dry_run"] is True  # SMS_PROVIDER defaults to dry_run
    run = db.scalar(select(AdviceRun))
    assert run.status == "dry_run" and run.recipients == 1
    message = db.scalar(select(AdvisoryMessage).where(AdvisoryMessage.purpose == "irrigation_schedule"))
    assert message.status == "dry_run"


def test_weekly_advice_skips_sectors_without_readings(db, monkeypatch):
    monkeypatch.setattr("app.services.forecast.get_settings", lambda: Settings(_env_file=None, weather_forecast_enabled=False))
    sector = Sector(name="Mareba", latitude=-2.3, longitude=30.2)
    db.add(sector)
    db.flush()
    cell = Cell(name="Kabuye", sector_id=sector.id, latitude=-2.31, longitude=30.21)
    db.add(cell)
    db.flush()
    db.add(FieldUser(phone_number="+250788000002", role=UserRole.farmer, cell_id=cell.id))
    db.commit()
    summary = advisory.send_weekly_advice(db)
    assert summary["sectors"] == [] and summary["no_readings"] == 1
    assert db.scalar(select(func.count()).select_from(AdviceRun)) == 0
    assert db.scalar(select(func.count()).select_from(AdvisoryMessage)) == 0


def test_weekly_advice_status_reports_last_and_next_run(db, monkeypatch):
    seed(db)
    settings = Settings(_env_file=None, advice_schedule_enabled=True, advice_schedule_weekday="tue", advice_schedule_time="06:30")
    monkeypatch.setattr(advisory, "get_settings", lambda: settings)
    status = advisory.weekly_advice_status(db)
    assert status["enabled"] is True and status["last_run"] is None
    assert status["next_run"] is not None and status["next_run"].weekday() == 1  # Tuesday
    assert (status["next_run"].hour, status["next_run"].minute) == (6, 30)
    # Once a run exists, the status reports it.
    advisory.send_weekly_advice(db)
    status = advisory.weekly_advice_status(db)
    assert status["last_run"] is not None and status["last_run"]["recipients"] == 1


def test_next_advice_run_is_none_when_disabled(monkeypatch):
    settings = Settings(_env_file=None, advice_schedule_enabled=False)
    monkeypatch.setattr(advisory, "get_settings", lambda: settings)
    assert advisory.next_advice_run(settings) is None


def test_next_advice_run_is_in_the_future(monkeypatch):
    settings = Settings(_env_file=None, advice_schedule_enabled=True, advice_schedule_weekday="mon", advice_schedule_time="06:00")
    now = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)  # a Wednesday
    run = advisory.next_advice_run(settings, now=now)
    assert run is not None and run > now.astimezone(advisory.KIGALI)
    assert (run - now.astimezone(advisory.KIGALI)) <= timedelta(days=7)
    assert run.weekday() == 0 and (run.hour, run.minute) == (6, 0)
