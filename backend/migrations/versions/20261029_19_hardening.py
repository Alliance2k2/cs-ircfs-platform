"""Week-1 hardening: consent, gateway idempotency, and reward milestones.

* ``field_users`` gains ``consent_at`` (first inbound message) and ``opted_out_at``
  (HAGARIKA/STOP). Broadcasts skip opted-out people. ``cell_id`` is indexed because
  every broadcast resolves recipients by cell.
* ``inbound_messages`` gains the unique ``(channel, session_id, text)`` constraint that
  makes a gateway retry replay the stored reply instead of recording a second report.
  A ``created_at`` index supports the recent-message views.
* ``incentive_rewards`` gains ``milestone`` with a unique per-user constraint, so a
  milestone can never be paid twice. Existing rows keep a NULL milestone: the
  constraint ignores NULLs, so historical payouts are preserved untouched.

Idempotent: each step checks the current shape first.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261029_19"
down_revision = "20261011_18"
branch_labels = None
depends_on = None

INBOUND_UNIQUE = "uq_inbound_channel_session_text"
REWARD_UNIQUE = "uq_reward_user_milestone"


def _columns(inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _indexes(inspector, table: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table) if index["name"]}


def _unique(inspector, table: str) -> set[str]:
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table) if constraint["name"]}


def _dedupe_inbound() -> None:
    """Drop retry rows written before the constraint existed, keeping the first.

    Rows without a session id are exempt from the uniqueness rule (SQL treats NULLs as
    distinct), and they are left alone: they cannot be matched to a retry anyway.
    """
    op.execute(
        "DELETE FROM inbound_messages WHERE session_id IS NOT NULL AND id NOT IN ("
        "SELECT MIN(id) FROM inbound_messages WHERE session_id IS NOT NULL "
        "GROUP BY channel, session_id, text)"
    )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    columns = _columns(inspector, "field_users")
    if "consent_at" not in columns:
        with op.batch_alter_table("field_users") as batch:
            batch.add_column(sa.Column("consent_at", sa.DateTime(timezone=False), nullable=True))
            batch.add_column(sa.Column("opted_out_at", sa.DateTime(timezone=False), nullable=True))
    indexes = _indexes(inspector, "field_users")
    if "ix_field_users_opted_out_at" not in indexes:
        op.create_index("ix_field_users_opted_out_at", "field_users", ["opted_out_at"])
    if "ix_field_users_cell_id" not in indexes:
        op.create_index("ix_field_users_cell_id", "field_users", ["cell_id"])

    columns = _columns(inspector, "inbound_messages")
    if INBOUND_UNIQUE not in _unique(inspector, "inbound_messages"):
        _dedupe_inbound()
        with op.batch_alter_table("inbound_messages") as batch:
            batch.create_unique_constraint(INBOUND_UNIQUE, ["channel", "session_id", "text"])
    if "ix_inbound_messages_created_at" not in _indexes(inspector, "inbound_messages"):
        op.create_index("ix_inbound_messages_created_at", "inbound_messages", ["created_at"])

    if "milestone" not in _columns(inspector, "incentive_rewards"):
        with op.batch_alter_table("incentive_rewards") as batch:
            batch.add_column(sa.Column("milestone", sa.Integer(), nullable=True))
    if REWARD_UNIQUE not in _unique(inspector, "incentive_rewards"):
        with op.batch_alter_table("incentive_rewards") as batch:
            batch.create_unique_constraint(REWARD_UNIQUE, ["field_user_id", "milestone"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if REWARD_UNIQUE in _unique(inspector, "incentive_rewards"):
        with op.batch_alter_table("incentive_rewards") as batch:
            batch.drop_constraint(REWARD_UNIQUE, type_="unique")
    if "milestone" in _columns(inspector, "incentive_rewards"):
        with op.batch_alter_table("incentive_rewards") as batch:
            batch.drop_column("milestone")

    if "ix_inbound_messages_created_at" in _indexes(inspector, "inbound_messages"):
        op.drop_index("ix_inbound_messages_created_at", table_name="inbound_messages")
    if INBOUND_UNIQUE in _unique(inspector, "inbound_messages"):
        with op.batch_alter_table("inbound_messages") as batch:
            batch.drop_constraint(INBOUND_UNIQUE, type_="unique")

    if "ix_field_users_cell_id" in _indexes(inspector, "field_users"):
        op.drop_index("ix_field_users_cell_id", table_name="field_users")
    if "ix_field_users_opted_out_at" in _indexes(inspector, "field_users"):
        op.drop_index("ix_field_users_opted_out_at", table_name="field_users")
    if "consent_at" in _columns(inspector, "field_users"):
        with op.batch_alter_table("field_users") as batch:
            batch.drop_column("opted_out_at")
            batch.drop_column("consent_at")
