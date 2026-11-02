"""Preserve existing service areas and allow multi-sector scheme coverage."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_25"
down_revision = "20261102_24"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("scheme_sector_coverage",
        sa.Column("scheme_id", sa.Integer(), sa.ForeignKey("irrigation_schemes.id"), primary_key=True),
        sa.Column("sector_id", sa.Integer(), sa.ForeignKey("sectors.id"), primary_key=True))
    op.execute("INSERT INTO scheme_sector_coverage (scheme_id, sector_id) "
               "SELECT id, sector_id FROM irrigation_schemes WHERE sector_id IS NOT NULL")


def downgrade():
    op.drop_table("scheme_sector_coverage")
