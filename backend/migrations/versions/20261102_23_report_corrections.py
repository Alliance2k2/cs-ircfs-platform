"""Retain original reports and link corrections to their replacement."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_23"
down_revision = "20261102_22"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("citizen_science_logs", "irrigation_climate_logs"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("superseded_by_id", sa.Integer(), nullable=True))
            batch.add_column(sa.Column("correction_reason", sa.Text(), nullable=True))


def downgrade():
    for table in ("citizen_science_logs", "irrigation_climate_logs"):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("correction_reason")
            batch.drop_column("superseded_by_id")
