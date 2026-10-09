"""Weekly automatic advice runs (WP2).

Records each sector's automatic irrigation-advice send per week so the scheduler and
the cron script are idempotent (one send per sector per week) and auditable.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261009_13"
down_revision = "20261009_12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "advice_runs" in inspector.get_table_names():
        return
    op.create_table(
        "advice_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("week_key", sa.String(10), nullable=False),
        sa.Column("sector_id", sa.Integer(), sa.ForeignKey("sectors.id"), nullable=False),
        sa.Column("recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("week_key", "sector_id", name="uq_advice_run_week_sector"),
    )
    op.create_index("ix_advice_runs_week_key", "advice_runs", ["week_key"])
    op.create_index("ix_advice_runs_sector_id", "advice_runs", ["sector_id"])


def downgrade() -> None:
    op.drop_index("ix_advice_runs_sector_id", table_name="advice_runs")
    op.drop_index("ix_advice_runs_week_key", table_name="advice_runs")
    op.drop_table("advice_runs")
