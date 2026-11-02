"""Add season, harvested area, harvest date and crop/season yield targets."""
from alembic import op
import sqlalchemy as sa

revision = "20261029_20"
down_revision = "20261029_19"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    crop_columns = _columns("citizen_science_logs")
    with op.batch_alter_table("citizen_science_logs") as batch:
        if "cultivated_area_hectares" not in crop_columns:
            batch.add_column(sa.Column("cultivated_area_hectares", sa.Float(), nullable=True))
        if "harvest_date" not in crop_columns:
            batch.add_column(sa.Column("harvest_date", sa.Date(), nullable=True))
        if "season" not in crop_columns:
            batch.add_column(sa.Column("season", sa.String(length=20), nullable=True))

    scheme_columns = _columns("irrigation_schemes")
    with op.batch_alter_table("irrigation_schemes") as batch:
        if "target_crop_type" not in scheme_columns:
            batch.add_column(sa.Column("target_crop_type", sa.String(length=80), nullable=True))
        if "target_season" not in scheme_columns:
            batch.add_column(sa.Column("target_season", sa.String(length=20), nullable=True))
        if "target_yield_tons_per_hectare" not in scheme_columns:
            batch.add_column(sa.Column("target_yield_tons_per_hectare", sa.Float(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("citizen_science_logs")}
    if "ix_citizen_science_logs_season" not in indexes:
        op.create_index("ix_citizen_science_logs_season", "citizen_science_logs", ["season"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("citizen_science_logs")}
    if "ix_citizen_science_logs_season" in indexes:
        op.drop_index("ix_citizen_science_logs_season", table_name="citizen_science_logs")
    with op.batch_alter_table("citizen_science_logs") as batch:
        batch.drop_column("season")
        batch.drop_column("harvest_date")
        batch.drop_column("cultivated_area_hectares")
    with op.batch_alter_table("irrigation_schemes") as batch:
        batch.drop_column("target_yield_tons_per_hectare")
        batch.drop_column("target_season")
        batch.drop_column("target_crop_type")
