"""Use persisted SMS and reward rows as a transactional delivery outbox."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_27"
down_revision = "20261102_26"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("advisory_messages", "incentive_rewards"):
        op.add_column(table, sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0"))
        op.add_column(table, sa.Column("last_attempt_at", sa.DateTime(), nullable=True))


def downgrade():
    for table in ("incentive_rewards", "advisory_messages"):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("last_attempt_at")
            batch.drop_column("delivery_attempts")
