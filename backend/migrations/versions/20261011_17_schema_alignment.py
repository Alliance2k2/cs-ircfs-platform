"""Align the database with the models: case assignments point at staff accounts.

Found by comparing a freshly migrated database with the models (October 2026):

* ``incident_cases.assigned_to_account_id`` and ``incident_events.changed_by_account_id``
  were renamed from ``*_user_id`` by 20261008_11 but still referenced ``field_users``,
  so on PostgreSQL assigning a case to a staff account could violate the foreign key.
  They now reference ``platform_accounts``; values that match no account are cleared.
* ``created_at`` on six tables created before the models declared it NOT NULL becomes
  NOT NULL (missing values are filled with the current time first).
* ``ix_incentive_rewards_user_id`` is renamed to match its column, ``field_user_id``.

Idempotent: each step checks the current shape first.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261011_17"
down_revision = "20261010_16"
branch_labels = None
depends_on = None

ACCOUNT_REFERENCES = (("incident_cases", "assigned_to_account_id"), ("incident_events", "changed_by_account_id"))
CREATED_AT_TABLES = ("advisory_messages", "auth_sessions", "inbound_messages", "incentive_rewards", "nutrition_surveys", "platform_accounts")
# Lets batch mode (SQLite) name the unnamed foreign keys so it can drop them.
NAMING = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}


def _foreign_key(table: str, column: str):
    for fk in sa.inspect(op.get_bind()).get_foreign_keys(table):
        if fk["constrained_columns"] == [column]:
            return fk
    return None


def _repoint(table: str, column: str, target: str, old_target: str) -> None:
    fk = _foreign_key(table, column)
    if fk is not None and fk["referred_table"] == target:
        return
    if target == "platform_accounts":
        op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IS NOT NULL AND {column} NOT IN (SELECT id FROM platform_accounts)")
    new_name = f"fk_{table}_{column}_{target}"
    with op.batch_alter_table(table, naming_convention=NAMING) as batch:
        if fk is not None:
            batch.drop_constraint(fk["name"] or f"fk_{table}_{column}_{old_target}", type_="foreignkey")
        batch.create_foreign_key(new_name, target, [column], ["id"])


def upgrade() -> None:
    for table, column in ACCOUNT_REFERENCES:
        _repoint(table, column, "platform_accounts", "field_users")

    inspector = sa.inspect(op.get_bind())
    for table in CREATED_AT_TABLES:
        created = next(column for column in inspector.get_columns(table) if column["name"] == "created_at")
        if created["nullable"]:
            op.execute(f"UPDATE {table} SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            with op.batch_alter_table(table) as batch:
                batch.alter_column("created_at", existing_type=sa.DateTime(timezone=True), nullable=False,
                                   existing_server_default=sa.text("CURRENT_TIMESTAMP"))

    indexes = {index["name"] for index in inspector.get_indexes("incentive_rewards")}
    if "ix_incentive_rewards_user_id" in indexes:
        op.drop_index("ix_incentive_rewards_user_id", table_name="incentive_rewards")
    if "ix_incentive_rewards_field_user_id" not in indexes:
        op.create_index("ix_incentive_rewards_field_user_id", "incentive_rewards", ["field_user_id"])


def downgrade() -> None:
    # The NOT NULL columns and the index name are kept: both are compatible with 20261010_16.
    for table, column in ACCOUNT_REFERENCES:
        fk = _foreign_key(table, column)
        if fk is not None and fk["referred_table"] == "platform_accounts":
            op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IS NOT NULL AND {column} NOT IN (SELECT id FROM field_users)")
            with op.batch_alter_table(table, naming_convention=NAMING) as batch:
                batch.drop_constraint(fk["name"] or f"fk_{table}_{column}_platform_accounts", type_="foreignkey")
                batch.create_foreign_key(f"fk_{table}_{column}_field_users", "field_users", [column], ["id"])
