"""Persist field USSD language without inferring a new caller's preference."""
from alembic import op
import sqlalchemy as sa

revision = "20261113_29"
down_revision = "20261102_28"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("field_users", sa.Column("ussd_language", sa.String(2), nullable=True))
    # Preserve the previous field experience for existing profiles only.
    op.execute("UPDATE field_users SET ussd_language = 'rw'")
    with op.batch_alter_table("field_users") as batch:
        batch.create_check_constraint("ck_field_users_ussd_language", "ussd_language IS NULL OR ussd_language IN ('rw', 'en')")


def downgrade():
    with op.batch_alter_table("field_users") as batch:
        batch.drop_constraint("ck_field_users_ussd_language", type_="check")
        batch.drop_column("ussd_language")
