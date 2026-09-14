"""Initial CS-IRCFS schema.

Revision ID: 20260911_01
Revises:
"""
from alembic import op

from app.db.base import Base
import app.db.models  # noqa: F401 - imports all models into Base metadata

revision = "20260911_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Initial baseline only. Later changes must use explicit Alembic revisions.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    Base.metadata.create_all(bind=op.get_bind(), tables=[table for table in Base.metadata.sorted_tables if table.name not in {"incident_cases", "incident_events"}])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[table for table in Base.metadata.sorted_tables if table.name not in {"incident_cases", "incident_events"}])
