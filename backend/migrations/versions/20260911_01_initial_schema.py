"""Initial CS-IRCFS schema.

Revision ID: 20260911_01
Revises:

The baseline creates only the tables that no later revision owns. Everything added
later (cases, platform accounts, messaging, the channel tables, and account_sectors) is
created by its own revision, so `alembic upgrade head` applies cleanly on a fresh
database as well as incrementally.
"""
from alembic import op

from app.db.base import Base
import app.db.models  # noqa: F401 - imports all models into Base metadata

revision = "20260911_01"
down_revision = None
branch_labels = None
depends_on = None

# Tables created by later revisions (03-10); the baseline must leave them alone.
LATER_TABLES = {
    "farms",
    "incident_cases",
    "incident_events",
    "platform_accounts",
    "advisory_messages",
    "auth_sessions",
    "inbound_messages",
    "nutrition_surveys",
    "incentive_rewards",
    "account_sectors",
    # Its changed_by_account_id points at platform_accounts, so it is created right after
    # that table in 20260929_05 (a fresh database failed here before October 2026).
    "community_feedback_events",
}


def _baseline_tables():
    return [table for table in Base.metadata.sorted_tables if table.name not in LATER_TABLES]


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    Base.metadata.create_all(bind=op.get_bind(), tables=_baseline_tables())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=list(reversed(_baseline_tables())))
