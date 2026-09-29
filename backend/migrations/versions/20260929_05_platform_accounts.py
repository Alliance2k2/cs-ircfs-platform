"""create platform accounts
Revision ID: 20260929_05
"""
from alembic import op
import sqlalchemy as sa
revision = "20260929_05"
down_revision = "20260914_04"
def upgrade():
    op.create_table("platform_accounts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(254), nullable=False, unique=True), sa.Column("password_hash", sa.String(256), nullable=False), sa.Column("full_name", sa.String(160), nullable=False), sa.Column("role", sa.String(40), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="active"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
def downgrade(): op.drop_table("platform_accounts")
