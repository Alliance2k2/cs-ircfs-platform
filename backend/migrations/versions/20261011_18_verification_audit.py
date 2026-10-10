"""Report verification and the audit log.

* ``citizen_science_logs`` and ``irrigation_climate_logs`` gain ``verification_status``
  (unverified / verified / rejected, default unverified), ``verified_by_account_id``,
  ``verified_at`` and ``verification_note``. Existing reports become ``unverified``.
* ``audit_events`` records who changed what (accounts, cases, grievances, verification,
  schemes, advice sends).

Idempotent: each step checks the current shape first.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261011_18"
down_revision = "20261011_17"
branch_labels = None
depends_on = None

REPORT_TABLES = ("citizen_science_logs", "irrigation_climate_logs")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in REPORT_TABLES:
        columns = {column["name"] for column in inspector.get_columns(table)}
        if "verification_status" in columns:
            continue
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("verification_status", sa.String(12), nullable=False, server_default="unverified"))
            batch.add_column(sa.Column("verified_by_account_id", sa.Integer(), nullable=True))
            batch.add_column(sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
            batch.add_column(sa.Column("verification_note", sa.Text(), nullable=True))
            batch.create_foreign_key(f"fk_{table}_verified_by_account_id_platform_accounts", "platform_accounts", ["verified_by_account_id"], ["id"])
        op.create_index(f"ix_{table}_verification_status", table, ["verification_status"])

    if "audit_events" not in inspector.get_table_names():
        op.create_table(
            "audit_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("actor_account_id", sa.Integer(), nullable=True),
            sa.Column("actor_label", sa.String(254), nullable=False),
            sa.Column("action", sa.String(60), nullable=False),
            sa.Column("entity", sa.String(40), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["actor_account_id"], ["platform_accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("actor_account_id", "action", "entity", "created_at"):
            op.create_index(f"ix_audit_events_{column}", "audit_events", [column])


def downgrade() -> None:
    op.drop_table("audit_events")
    for table in REPORT_TABLES:
        op.drop_index(f"ix_{table}_verification_status", table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f"fk_{table}_verified_by_account_id_platform_accounts", type_="foreignkey")
            for column in ("verification_note", "verified_at", "verified_by_account_id", "verification_status"):
                batch.drop_column(column)
