"""Track actionable crop and infrastructure reports as cases.

Revision ID: 20260914_04
Revises: 20260914_03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260914_04"
down_revision = "20260914_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = sa.inspect(bind).get_table_names()
    status_type = postgresql.ENUM("open", "triaged", "assigned", "in_progress", "resolved", "closed", name="reportstatus", create_type=False) if bind.dialect.name == "postgresql" else sa.Enum("open", "triaged", "assigned", "in_progress", "resolved", "closed", name="reportstatus")

    if "incident_cases" not in existing:
        op.create_table(
            "incident_cases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_type", sa.String(30), nullable=False),
            sa.Column("source_id", sa.Integer(), nullable=False),
            sa.Column("priority", sa.String(12), nullable=False),
            sa.Column("status", status_type, nullable=False),
            sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("field_users.id")),
            sa.Column("due_at", sa.DateTime(timezone=True)),
            sa.Column("action_taken", sa.Text()),
            sa.Column("reporter_notified_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("source_type", "source_id", name="uq_incident_source"),
        )
        op.create_index("ix_incident_cases_source_type", "incident_cases", ["source_type"])

    if "incident_events" not in existing:
        op.create_table(
            "incident_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("incident_cases.id"), nullable=False),
            sa.Column("previous_status", status_type),
            sa.Column("new_status", status_type, nullable=False),
            sa.Column("action_taken", sa.Text()),
            sa.Column("changed_by_user_id", sa.Integer(), sa.ForeignKey("field_users.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_incident_events_case_id", "incident_events", ["case_id"])


def downgrade() -> None:
    op.drop_table("incident_events")
    op.drop_table("incident_cases")
