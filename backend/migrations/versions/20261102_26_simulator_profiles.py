"""Isolate training profiles and inbound retry keys from real field callers."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_26"
down_revision = "20261102_25"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("field_users", sa.Column("data_origin", sa.String(12), nullable=False, server_default="field"))
    op.create_index("ix_field_users_data_origin", "field_users", ["data_origin"])
    with op.batch_alter_table("inbound_messages") as batch:
        batch.drop_constraint("uq_inbound_channel_session_text", type_="unique")
        batch.create_unique_constraint("uq_inbound_channel_session_origin", ["channel", "session_id", "text", "data_origin"])


def downgrade():
    op.execute("UPDATE inbound_messages SET session_id = 'simulator:' || CAST(id AS VARCHAR) "
               "WHERE data_origin = 'simulator' AND session_id IS NOT NULL")
    with op.batch_alter_table("inbound_messages") as batch:
        batch.drop_constraint("uq_inbound_channel_session_origin", type_="unique")
        batch.create_unique_constraint("uq_inbound_channel_session_text", ["channel", "session_id", "text"])
    op.drop_index("ix_field_users_data_origin", table_name="field_users")
    with op.batch_alter_table("field_users") as batch:
        batch.drop_column("data_origin")
