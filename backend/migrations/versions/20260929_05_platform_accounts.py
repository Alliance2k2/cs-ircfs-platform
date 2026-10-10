"""create platform accounts
Revision ID: 20260929_05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "20260929_05"
down_revision = "20260914_04"
def upgrade():
    op.create_table("platform_accounts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(254), nullable=False, unique=True), sa.Column("password_hash", sa.String(256), nullable=False), sa.Column("full_name", sa.String(160), nullable=False), sa.Column("role", sa.String(40), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="active"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    # A fresh database: the baseline (20260911_01) leaves community_feedback_events to this
    # revision because it references platform_accounts. Existing databases already have it.
    if "community_feedback_events" not in sa.inspect(op.get_bind()).get_table_names():
        statuses = ("open", "triaged", "assigned", "in_progress", "resolved", "closed")
        # The baseline already created the reportstatus type on PostgreSQL: reuse it.
        status = sa.Enum(*statuses, name="reportstatus").with_variant(
            postgresql.ENUM(*statuses, name="reportstatus", create_type=False), "postgresql")
        op.create_table(
            "community_feedback_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("feedback_id", sa.Integer(), nullable=False),
            sa.Column("previous_status", status, nullable=True),
            sa.Column("new_status", status, nullable=False),
            sa.Column("action_taken", sa.Text(), nullable=True),
            sa.Column("changed_by_account_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["changed_by_account_id"], ["platform_accounts.id"]),
            sa.ForeignKeyConstraint(["feedback_id"], ["community_feedback.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_community_feedback_events_feedback_id"), "community_feedback_events", ["feedback_id"], unique=False)


def downgrade():
    if "community_feedback_events" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("community_feedback_events")
    op.drop_table("platform_accounts")
