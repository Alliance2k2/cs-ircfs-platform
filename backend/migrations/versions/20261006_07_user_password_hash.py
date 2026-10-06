"""Add optional password hash column to agricultural users.

Platform login accounts use ``platform_accounts``; this column preserves
compatibility with older user records and the current ORM model.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261006_07"
down_revision = "20261005_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
