"""Record where every field record came from.

``data_origin`` separates real field reports from simulator tests, seeded demonstration
rows and bulk imports, so dashboards never mistake one for the other:

* ``field`` — a citizen through the USSD/SMS gateway or a staff API call (the default),
* ``simulator`` — the on-screen phone simulator used for training and testing,
* ``demo`` — rows written by scripts/seed_demo_data.py,
* ``import`` — rows loaded from historical files by an import script.

Existing rows become ``field``. The migration is idempotent.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261010_16"
down_revision = "20261009_15"
branch_labels = None
depends_on = None

TABLES = ("citizen_science_logs", "irrigation_climate_logs", "nutrition_surveys", "community_feedback", "inbound_messages")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in TABLES:
        if "data_origin" in {column["name"] for column in inspector.get_columns(table)}:
            continue
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("data_origin", sa.String(12), nullable=False, server_default="field"))
        op.create_index(f"ix_{table}_data_origin", table, ["data_origin"])


def downgrade() -> None:
    for table in TABLES:
        op.drop_index(f"ix_{table}_data_origin", table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_column("data_origin")
