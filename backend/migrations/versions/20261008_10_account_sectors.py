"""Area-level access: link platform accounts to the sectors they work in.

An account with no linked sectors keeps district-wide access, so existing
accounts are unaffected.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261008_10"
down_revision = "20261007_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_sectors",
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("platform_accounts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("sector_id", sa.Integer(), sa.ForeignKey("sectors.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("account_sectors")
