"""Add scientific provenance and versioned scheme targets without inferring legacy values."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_22"
down_revision = "20261029_21"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("citizen_science_logs") as batch:
        for name, kind in (
            ("harvested_area_hectares", sa.Float()), ("observed_quantity", sa.Float()),
            ("harvest_unit", sa.String(10)), ("observation_type", sa.String(30)),
            ("data_source", sa.String(255)), ("reference_year", sa.Integer()), ("reporting_date", sa.Date()),
        ):
            batch.add_column(sa.Column(name, kind, nullable=True))
    op.create_table(
        "scheme_baselines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scheme_id", sa.Integer(), sa.ForeignKey("irrigation_schemes.id"), nullable=False),
        sa.Column("crop_type", sa.String(80), nullable=False),
        sa.Column("season", sa.String(20), nullable=False),
        sa.Column("reference_year", sa.Integer(), nullable=False),
        sa.Column("expected_yield", sa.Float(), nullable=False),
        sa.Column("yield_unit", sa.String(10), nullable=False),
        sa.Column("official_source", sa.String(255), nullable=False),
        sa.Column("document_reference", sa.String(255), nullable=False),
        sa.Column("data_origin", sa.String(12), nullable=False, server_default="field"),
        sa.Column("verification_status", sa.String(12), nullable=False, server_default="unverified"),
        sa.Column("approved_at", sa.Date(), nullable=True),
        sa.Column("approved_by_account_id", sa.Integer(), sa.ForeignKey("platform_accounts.id"), nullable=True),
        sa.Column("supersedes_id", sa.Integer(), sa.ForeignKey("scheme_baselines.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_scheme_baselines_scheme_id", "scheme_baselines", ["scheme_id"])
    op.create_index("ix_scheme_baselines_data_origin", "scheme_baselines", ["data_origin"])


def downgrade():
    op.drop_table("scheme_baselines")
    with op.batch_alter_table("citizen_science_logs") as batch:
        for name in ("harvested_area_hectares", "observed_quantity", "harvest_unit", "observation_type",
                     "data_source", "reference_year", "reporting_date"):
            batch.drop_column(name)
