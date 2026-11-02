"""Store consent timestamps without timezone metadata, as the UTC type decorator expects."""
from alembic import op
import sqlalchemy as sa

revision = "20261029_21"
down_revision = "20261029_20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("field_users") as batch:
        batch.alter_column("consent_at", existing_type=sa.DateTime(timezone=True), type_=sa.DateTime(timezone=False))
        batch.alter_column("opted_out_at", existing_type=sa.DateTime(timezone=True), type_=sa.DateTime(timezone=False))


def downgrade() -> None:
    with op.batch_alter_table("field_users") as batch:
        batch.alter_column("consent_at", existing_type=sa.DateTime(timezone=False), type_=sa.DateTime(timezone=True))
        batch.alter_column("opted_out_at", existing_type=sa.DateTime(timezone=False), type_=sa.DateTime(timezone=True))
