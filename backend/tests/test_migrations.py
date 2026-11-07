"""Alembic migrations: a fresh database matches the models, and existing data survives upgrades.

Runs on SQLite files. CI runs the same upgrade and schema check on a clean PostGIS server.
"""
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings
from scripts.check_schema import differences

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture()
def database(tmp_path, monkeypatch):
    """A migration config pointed at an empty SQLite file (env.py reads DATABASE_URL)."""
    url = f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    yield config, url
    get_settings.cache_clear()


def test_a_fresh_database_matches_the_models(database):
    config, url = database
    command.upgrade(config, "head")
    assert differences(url) == []


def test_migrations_do_not_disable_application_observability(database):
    import logging

    logger = logging.getLogger("app.main")
    logger.disabled = False
    config, _ = database
    command.upgrade(config, "head")
    assert logger.disabled is False


def test_upgrading_existing_data_keeps_it_and_points_assignments_at_accounts(database):
    config, url = database
    command.upgrade(config, "20261010_16")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO platform_accounts (id, email, full_name, password_hash, role, status) "
                                "VALUES (7, 'officer@example.org', 'Officer', 'x', 'district_officer', 'active')"))
        connection.execute(text("INSERT INTO citizen_science_logs (id, crop_type, data_origin) VALUES (1, 'Maize', 'field'), (2, 'Beans', 'field')"))
        connection.execute(text("INSERT INTO incident_cases (id, source_type, source_id, priority, status, assigned_to_account_id) "
                                "VALUES (1, 'crop', 1, 'critical', 'assigned', 7)"))
        connection.execute(text("INSERT INTO incident_cases (id, source_type, source_id, priority, status, assigned_to_account_id) "
                                "VALUES (2, 'crop', 2, 'high', 'assigned', 999)"))  # no such account
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(url)
    references = {tuple(fk["constrained_columns"]): fk["referred_table"] for fk in inspect(engine).get_foreign_keys("incident_cases")}
    assert references[("assigned_to_account_id",)] == "platform_accounts"
    with engine.connect() as connection:
        rows = dict(connection.execute(text("SELECT id, assigned_to_account_id FROM incident_cases")).all())
    assert rows == {1: 7, 2: None}  # a real assignment is kept; one pointing at no account is cleared
    engine.dispose()
    assert differences(url) == []


def test_the_latest_migration_downgrades_and_upgrades_again(database):
    config, url = database
    command.upgrade(config, "head")
    command.downgrade(config, "-1")
    command.upgrade(config, "head")
    assert differences(url) == []


def test_every_name_fits_postgresql(database):
    """PostgreSQL rejects identifiers over 63 characters; SQLite does not, so check here."""
    config, url = database
    command.upgrade(config, "head")
    engine = create_engine(url)
    inspector = inspect(engine)
    names = []
    for table in inspector.get_table_names():
        names.append(table)
        names += [column["name"] for column in inspector.get_columns(table)]
        names += [item["name"] for item in inspector.get_indexes(table) + inspector.get_foreign_keys(table) + inspector.get_unique_constraints(table)
                  if item.get("name")]
    engine.dispose()
    assert [name for name in names if len(name) > 63] == []


def test_scientific_upgrade_preserves_legacy_area_without_inventing_harvested_area(database):
    config, url = database
    command.upgrade(config, "20261029_21")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO citizen_science_logs (id, crop_type, cultivated_area_hectares, reported_harvest_tons) VALUES (21, 'Rice', 3, 4)"))
        connection.execute(text("INSERT INTO irrigation_schemes (id, name, baseline_yield_target_tons, baseline_source, is_active) VALUES (21, 'Legacy scheme', 50, 'Old study', 1)"))
    engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.connect() as connection:
        row = connection.execute(text("SELECT cultivated_area_hectares, harvested_area_hectares, reported_harvest_tons, observation_type FROM citizen_science_logs WHERE id=21")).one()
        assert tuple(row) == (3, None, 4, None)
        assert connection.scalar(text("SELECT COUNT(*) FROM scheme_baselines")) == 0
        assert connection.scalar(text("SELECT baseline_yield_target_tons FROM irrigation_schemes WHERE id=21")) == 50
    engine.dispose()


def test_climate_upgrade_does_not_invent_observation_dates_or_outage_intervals(database):
    config, url = database
    command.upgrade(config, "20261102_23")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO irrigation_climate_logs (id, rainfall_mm, infrastructure_name, operational_status) VALUES (31, 12, 'Legacy pump', 'offline')"))
    engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.connect() as connection:
        assert tuple(connection.execute(text("SELECT rainfall_mm, observation_date, data_source FROM irrigation_climate_logs WHERE id=31")).one()) == (12, None, None)
        assert connection.scalar(text("SELECT COUNT(*) FROM asset_outages")) == 0
        assert connection.scalar(text("SELECT COUNT(*) FROM rainfall_references")) == 0
    engine.dispose()
