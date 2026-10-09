"""create platform accounts
Revision ID: 20260929_05
"""
from alembic import op
import sqlalchemy as sa
revision = "20260929_05"
down_revision = "20260914_04"
def upgrade():
    op.create_table("platform_accounts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(254), nullable=False, unique=True), sa.Column("password_hash", sa.String(256), nullable=False), sa.Column("full_name", sa.String(160), nullable=False), sa.Column("role", sa.String(40), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="active"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    # A fresh database: the baseline (20260911_01) leaves community_feedback_events to this
    # revision because it references platform_accounts. Existing databases already have it.
    if "community_feedback_events" not in sa.inspect(op.get_bind()).get_table_names():
        from app.db.base import Base
        import app.db.models  # noqa: F401 - loads the table definition
        Base.metadata.tables["community_feedback_events"].create(bind=op.get_bind())


def downgrade():
    op.drop_table("platform_accounts")
