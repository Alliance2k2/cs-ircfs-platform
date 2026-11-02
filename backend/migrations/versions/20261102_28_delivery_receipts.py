"""Provider receipt journal and optional short-lived encrypted reply recipients."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_28"
down_revision = "20261102_27"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("advisory_messages", sa.Column("private_recipient", sa.Text(), nullable=True))
    op.add_column("advisory_messages", sa.Column("private_recipient_expires_at", sa.DateTime(), nullable=True))
    op.create_table("delivery_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("provider_id", sa.String(120), nullable=False),
        sa.Column("provider_status", sa.String(40), nullable=False),
        sa.Column("normalized_status", sa.String(20), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("kind", "provider_id", "provider_status", name="uq_delivery_receipt_event"))
    op.create_index("ix_delivery_receipts_provider_id", "delivery_receipts", ["provider_id"])


def downgrade():
    op.drop_index("ix_delivery_receipts_provider_id", table_name="delivery_receipts")
    op.drop_table("delivery_receipts")
    with op.batch_alter_table("advisory_messages") as batch:
        batch.drop_column("private_recipient_expires_at")
        batch.drop_column("private_recipient")
