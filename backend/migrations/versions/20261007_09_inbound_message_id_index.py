"""Index inbound messages by gateway message ID.

The SMS callback looks up the Africa's Talking message ID (stored in session_id)
to ignore retried deliveries, so the lookup must stay fast as messages grow.
"""

from alembic import op


revision = "20261007_09"
down_revision = "20261006_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_inbound_messages_session_id", "inbound_messages", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_inbound_messages_session_id", table_name="inbound_messages")
