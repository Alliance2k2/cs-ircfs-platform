"""Dated rain observations, documented reference windows and recorded maintenance."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_24"
down_revision = "20261102_23"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("irrigation_climate_logs") as batch:
        batch.add_column(sa.Column("observation_date", sa.Date(), nullable=True))
        batch.add_column(sa.Column("gauge_code", sa.String(80), nullable=True))
        batch.add_column(sa.Column("data_source", sa.String(255), nullable=True))
    op.create_index("ix_irrigation_climate_logs_observation_date", "irrigation_climate_logs", ["observation_date"])
    with op.batch_alter_table("scheme_assets") as batch:
        batch.add_column(sa.Column("cell_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_scheme_assets_cell_id_cells", "cells", ["cell_id"], ["id"])
    op.create_index("ix_scheme_assets_cell_id", "scheme_assets", ["cell_id"])

    op.create_table("rainfall_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sector_id", sa.Integer(), sa.ForeignKey("sectors.id"), nullable=True),
        sa.Column("scheme_id", sa.Integer(), sa.ForeignKey("irrigation_schemes.id"), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False), sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("reference_start_year", sa.Integer(), nullable=False), sa.Column("reference_end_year", sa.Integer(), nullable=False),
        sa.Column("mean_rainfall_mm", sa.Float(), nullable=False),
        sa.Column("source", sa.String(255), nullable=False), sa.Column("document_reference", sa.String(255), nullable=False),
        sa.Column("data_origin", sa.String(12), nullable=False, server_default="field"),
        sa.Column("approved_at", sa.Date(), nullable=True),
        sa.Column("approved_by_account_id", sa.Integer(), sa.ForeignKey("platform_accounts.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    for field in ("sector_id", "scheme_id", "data_origin"):
        op.create_index(f"ix_rainfall_references_{field}", "rainfall_references", [field])

    op.create_table("asset_outages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("scheme_assets.id"), nullable=False),
        sa.Column("cell_id", sa.Integer(), sa.ForeignKey("cells.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False), sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("category", sa.String(30), nullable=False), sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("repair_status", sa.String(20), nullable=False, server_default="reported"),
        sa.Column("data_origin", sa.String(12), nullable=False, server_default="field"),
        sa.Column("created_by_account_id", sa.Integer(), sa.ForeignKey("platform_accounts.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_table("asset_maintenance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("scheme_assets.id"), nullable=False),
        sa.Column("cell_id", sa.Integer(), sa.ForeignKey("cells.id"), nullable=True),
        sa.Column("outage_id", sa.Integer(), sa.ForeignKey("asset_outages.id"), nullable=True),
        sa.Column("performed_at", sa.DateTime(), nullable=False), sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("action", sa.Text(), nullable=False), sa.Column("source", sa.String(255), nullable=False),
        sa.Column("restored", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("data_origin", sa.String(12), nullable=False, server_default="field"),
        sa.Column("created_by_account_id", sa.Integer(), sa.ForeignKey("platform_accounts.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    for table, fields in (("asset_outages", ("asset_id", "cell_id", "data_origin")),
                          ("asset_maintenance", ("asset_id", "cell_id", "outage_id", "data_origin"))):
        for field in fields:
            op.create_index(f"ix_{table}_{field}", table, [field])


def downgrade():
    op.drop_table("asset_maintenance")
    op.drop_table("asset_outages")
    op.drop_table("rainfall_references")
    op.drop_index("ix_scheme_assets_cell_id", table_name="scheme_assets")
    with op.batch_alter_table("scheme_assets") as batch:
        batch.drop_constraint("fk_scheme_assets_cell_id_cells", type_="foreignkey")
        batch.drop_column("cell_id")
    op.drop_index("ix_irrigation_climate_logs_observation_date", table_name="irrigation_climate_logs")
    with op.batch_alter_table("irrigation_climate_logs") as batch:
        batch.drop_column("data_source")
        batch.drop_column("gauge_code")
        batch.drop_column("observation_date")
