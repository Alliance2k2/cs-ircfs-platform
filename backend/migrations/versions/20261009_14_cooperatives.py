"""Cooperatives, Data Champions and training records (WP5).

* creates the ``cooperatives`` table (name unique, sector, irrigation scheme,
  pilot flag, contact field user),
* adds ``cooperative_id``, ``is_data_champion``, ``trained_at`` and
  ``training_notes`` to ``field_users``,
* backfills one cooperative per distinct ``cooperative_name`` and links the
  field users to it, so no existing free-text value is lost.

``field_users.cooperative_name`` stays readable until the migration is
confirmed in production; the API keeps returning it.

The migration is idempotent: every step only runs when the old shape is present.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261009_14"
down_revision = "20261009_13"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "cooperatives" not in inspector.get_table_names():
        op.create_table(
            "cooperatives",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False, unique=True),
            sa.Column("sector_id", sa.Integer(), sa.ForeignKey("sectors.id"), nullable=True),
            sa.Column("irrigation_scheme_id", sa.Integer(), sa.ForeignKey("irrigation_schemes.id"), nullable=True),
            sa.Column("is_pilot", sa.Boolean(), nullable=False, server_default=sa.false()),
            # No foreign key: field_users already points at cooperatives (see models.py).
            sa.Column("contact_field_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cooperatives_name", "cooperatives", ["name"])

    columns = _columns("field_users")
    additions = []
    if "cooperative_id" not in columns:
        additions.append(sa.Column("cooperative_id", sa.Integer(), sa.ForeignKey("cooperatives.id"), nullable=True))
    if "is_data_champion" not in columns:
        additions.append(sa.Column("is_data_champion", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "trained_at" not in columns:
        additions.append(sa.Column("trained_at", sa.Date(), nullable=True))
    if "training_notes" not in columns:
        additions.append(sa.Column("training_notes", sa.Text(), nullable=True))
    if additions:
        with op.batch_alter_table("field_users") as batch:
            for column in additions:
                batch.add_column(column)
        op.create_index("ix_field_users_cooperative_id", "field_users", ["cooperative_id"])

    # Backfill: one cooperative per distinct non-empty cooperative_name, then link.
    op.execute(
        """
        INSERT INTO cooperatives (name)
        SELECT DISTINCT TRIM(cooperative_name)
        FROM field_users
        WHERE cooperative_name IS NOT NULL AND TRIM(cooperative_name) <> ''
        """
    )
    op.execute(
        """
        UPDATE field_users
        SET cooperative_id = (
            SELECT cooperatives.id FROM cooperatives
            WHERE cooperatives.name = TRIM(field_users.cooperative_name)
        )
        WHERE cooperative_name IS NOT NULL AND TRIM(cooperative_name) <> ''
        """
    )


def downgrade() -> None:
    columns = _columns("field_users")
    with op.batch_alter_table("field_users") as batch:
        for name in ("training_notes", "trained_at", "is_data_champion", "cooperative_id"):
            if name in columns:
                batch.drop_column(name)
    if "cooperatives" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_index("ix_cooperatives_name", table_name="cooperatives")
        op.drop_table("cooperatives")
