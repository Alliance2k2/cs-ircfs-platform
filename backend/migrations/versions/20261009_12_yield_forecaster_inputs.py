"""Yield forecaster inputs: crop variety and expected harvest month (WP1).

The USSD/SMS harvest flow now records *what* was planted (variety), *when* it was
planted (the existing planting_date) and *when* it is expected to be harvested,
so the monthly yield forecast has more than crop and tons to work with.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261009_12"
down_revision = "20261008_11"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    columns = _columns("citizen_science_logs")
    with op.batch_alter_table("citizen_science_logs") as batch:
        if "crop_variety" not in columns:
            batch.add_column(sa.Column("crop_variety", sa.String(80), nullable=True))
        if "expected_harvest_month" not in columns:
            batch.add_column(sa.Column("expected_harvest_month", sa.Date(), nullable=True))


def downgrade() -> None:
    columns = _columns("citizen_science_logs")
    with op.batch_alter_table("citizen_science_logs") as batch:
        if "expected_harvest_month" in columns:
            batch.drop_column("expected_harvest_month")
        if "crop_variety" in columns:
            batch.drop_column("crop_variety")
