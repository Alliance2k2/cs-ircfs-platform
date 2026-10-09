"""Split the two people systems: USSD/SMS callers become ``field_users``.

The old ``users`` table only ever held feature-phone callers, while web staff live in
``platform_accounts``. This renames the table and every column that referenced it so the
two systems are unmistakable, retires the unused ``farms`` table, and tightens the
incident-source vocabulary to ``crop`` / ``infrastructure``.

The migration is idempotent: it only performs each step when the old shape is present, so
it applies to a database migrated before the rename as well as to a fresh one.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261008_11"
down_revision = "20261008_10"
branch_labels = None
depends_on = None

RENAMES = (
    ("incentive_rewards", "user_id", "field_user_id"),
    ("community_feedback", "assigned_to_user_id", "assigned_to_field_user_id"),
    ("community_feedback_events", "changed_by_user_id", "changed_by_account_id"),
    ("incident_cases", "assigned_to_user_id", "assigned_to_account_id"),
    ("incident_events", "changed_by_user_id", "changed_by_account_id"),
)


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "farms" in inspector.get_table_names():
        op.drop_table("farms")

    if "users" in inspector.get_table_names():
        op.rename_table("users", "field_users")

    if "password_hash" in _columns("field_users"):
        with op.batch_alter_table("field_users") as batch:
            batch.drop_column("password_hash")

    for table, old, new in RENAMES:
        columns = _columns(table)
        if old in columns and new not in columns:
            with op.batch_alter_table(table) as batch:
                batch.alter_column(old, new_column_name=new)

    op.execute("UPDATE incident_cases SET source_type = 'infrastructure' WHERE source_type = 'irrigation'")
    checks = {check["name"] for check in sa.inspect(op.get_bind()).get_check_constraints("incident_cases")}
    with op.batch_alter_table("incident_cases") as batch:
        if "ck_incident_source_type" not in checks:
            batch.create_check_constraint("ck_incident_source_type", "source_type IN ('crop', 'infrastructure')")
        if "ck_incident_priority" not in checks:
            batch.create_check_constraint("ck_incident_priority", "priority IN ('critical', 'high', 'medium')")


def downgrade() -> None:
    op.execute("UPDATE incident_cases SET source_type = 'irrigation' WHERE source_type = 'infrastructure'")
    for table, old, new in reversed(RENAMES):
        columns = _columns(table)
        if new in columns and old not in columns:
            with op.batch_alter_table(table) as batch:
                batch.alter_column(new, new_column_name=old)
    if "password_hash" not in _columns("field_users"):
        with op.batch_alter_table("field_users") as batch:
            batch.add_column(sa.Column("password_hash", sa.String(256)))
    if "field_users" in sa.inspect(op.get_bind()).get_table_names():
        op.rename_table("field_users", "users")
