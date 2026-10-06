"""Field channels, persistent sessions, nutrition tracker, and airtime incentives.

Adds the tables behind the USSD/SMS gateway (architecture Section 4), the
Household Nutrition Tracker (Module 1), airtime rewards (Section 8.1), and
database-backed sign-in sessions. Also tags outbound SMS with a purpose and cell
so closing-the-loop blasts can be audited.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261006_08"
down_revision = "20261006_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("platform_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index("ix_auth_sessions_account_id", "auth_sessions", ["account_id"])

    op.add_column("advisory_messages", sa.Column("purpose", sa.String(30), nullable=True))
    op.add_column("advisory_messages", sa.Column("cell_id", sa.Integer(), sa.ForeignKey("cells.id"), nullable=True))
    op.create_index("ix_advisory_messages_purpose", "advisory_messages", ["purpose"])

    op.create_table(
        "inbound_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("session_id", sa.String(120)),
        sa.Column("text", sa.Text()),
        sa.Column("reply", sa.Text()),
        sa.Column("record_type", sa.String(40)),
        sa.Column("record_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_inbound_messages_phone_number", "inbound_messages", ["phone_number"])

    op.create_table(
        "nutrition_surveys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporter_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("cell_id", sa.Integer(), sa.ForeignKey("cells.id")),
        sa.Column("meals_per_day", sa.Integer(), nullable=False),
        sa.Column("ate_protein_or_vegetables", sa.Boolean(), nullable=False),
        sa.Column("food_sufficient", sa.Boolean(), nullable=False),
        sa.Column("stunting_risk_score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("stunting_risk_score BETWEEN 1 AND 5", name="ck_nutrition_risk_range"),
    )
    op.create_index("ix_nutrition_surveys_reporter_id", "nutrition_surveys", ["reporter_id"])
    op.create_index("ix_nutrition_surveys_cell_id", "nutrition_surveys", ["cell_id"])

    op.create_table(
        "incentive_rewards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("amount_rwf", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("provider_id", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_incentive_rewards_user_id", "incentive_rewards", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_incentive_rewards_user_id", table_name="incentive_rewards")
    op.drop_table("incentive_rewards")
    op.drop_index("ix_nutrition_surveys_cell_id", table_name="nutrition_surveys")
    op.drop_index("ix_nutrition_surveys_reporter_id", table_name="nutrition_surveys")
    op.drop_table("nutrition_surveys")
    op.drop_index("ix_inbound_messages_phone_number", table_name="inbound_messages")
    op.drop_table("inbound_messages")
    op.drop_index("ix_advisory_messages_purpose", table_name="advisory_messages")
    op.drop_column("advisory_messages", "cell_id")
    op.drop_column("advisory_messages", "purpose")
    op.drop_index("ix_auth_sessions_account_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_token_hash", table_name="auth_sessions")
    op.drop_table("auth_sessions")
