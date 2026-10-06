"""create advisory message log
Revision ID: 20261005_06
"""
from alembic import op
import sqlalchemy as sa

revision = "20261005_06"
down_revision = "20260929_05"

def upgrade():
    op.create_table(
        "advisory_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="rw"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False, server_default="sms"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("provider_id", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_advisory_messages_phone_number", "advisory_messages", ["phone_number"])

def downgrade():
    op.drop_index("ix_advisory_messages_phone_number", table_name="advisory_messages")
    op.drop_table("advisory_messages")
