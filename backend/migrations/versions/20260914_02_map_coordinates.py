"""Add verified map coordinates to geographic reference records."""
from alembic import op
import sqlalchemy as sa


revision = "20260914_02"
down_revision = "20260911_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("sectors", "cells", "irrigation_schemes"):
        existing = {column["name"] for column in inspector.get_columns(table)}
        for name in ("latitude", "longitude"):
            if name not in existing:
                op.add_column(table, sa.Column(name, sa.Float(), nullable=True))


def downgrade() -> None:
    # The baseline schema already contains these fields on fresh databases.
    pass
