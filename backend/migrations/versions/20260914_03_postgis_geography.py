"""Add PostGIS geometry storage for farmers, boundaries, and farms."""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


revision = "20260914_03"
down_revision = "20260914_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    for table in ("sectors", "cells", "irrigation_schemes"):
        if "boundary" not in {column["name"] for column in inspector.get_columns(table)}:
            op.add_column(table, sa.Column("boundary", Geometry("MULTIPOLYGON", srid=4326) if bind.dialect.name == "postgresql" else sa.Text(), nullable=True))
    if "location" not in {column["name"] for column in inspector.get_columns("field_users")}:
        op.add_column("field_users", sa.Column("location", Geometry("POINT", srid=4326) if bind.dialect.name == "postgresql" else sa.Text(), nullable=True))
    if "farms" not in inspector.get_table_names():
        op.create_table(
        "farms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("field_users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("boundary", Geometry("MULTIPOLYGON", srid=4326) if bind.dialect.name == "postgresql" else sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    # Baseline-created spatial fields must remain intact.
    pass
