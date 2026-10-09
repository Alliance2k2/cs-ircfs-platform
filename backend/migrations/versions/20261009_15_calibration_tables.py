"""Calibration tables for Section 9 (WP7).

* ``advisory_thresholds`` — per-sector rainfall thresholds that override the
  ``.env`` defaults, each with the source document it was calibrated from,
* ``grievance_categories`` and ``scheme_assets`` — the two USSD menus moved out
  of the code constants, seeded with today's values so the menus do not change,
* ``bottleneck_baselines`` — historical AfDB evaluation findings that ground the
  recurring-bottleneck rule.

The migration is idempotent: every step only runs when the old shape is present.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261009_15"
down_revision = "20261009_14"
branch_labels = None
depends_on = None

# Today's GRIEVANCES constant (ussd.py). label_en is stored in community_feedback.category.
GRIEVANCE_SEED = [
    ("input_distribution", "Ikwirakwizwa ry'inyongeramusaruro", "Input Distribution"),
    ("water_pricing", "Igiciro cy'amazi", "Water Pricing"),
    ("resettlement_downstream_impact", "Kwimurwa/ingaruka z'urugomero", "Resettlement/Downstream Impact"),
    ("operational_challenge", "Imikorere y'umushinga", "Operational Challenge"),
    ("other", "Ibindi", "Other"),
]

# Today's ASSETS constant (ussd.py): (name_rw, name_en, scheme prefix, asset type).
ASSET_SEED = [
    ("PADAB pompe 1", "PADAB Pumping Station 1", "PADAB", "pump"),
    ("PADAB pompe 2", "PADAB Pumping Station 2", "PADAB", "pump"),
    ("PADAB umuyoboro", "PADAB canal network (65.5 km)", "PADAB", "canal"),
    ("APEFA pompe Ngeruka", "APEFA solar pump - Ngeruka", "APEFA", "pump"),
    ("APEFA pompe Mareba", "APEFA solar pump - Mareba", "APEFA", "pump"),
]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()
    bind = op.get_bind()

    if "advisory_thresholds" not in tables:
        op.create_table(
            "advisory_thresholds",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("sector_id", sa.Integer(), sa.ForeignKey("sectors.id"), nullable=False, unique=True),
            sa.Column("dry_mm", sa.Float(), nullable=False),
            sa.Column("wet_mm", sa.Float(), nullable=False),
            sa.Column("source", sa.String(255), nullable=True),
            sa.Column("valid_from", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_advisory_thresholds_sector_id", "advisory_thresholds", ["sector_id"])

    if "grievance_categories" not in tables:
        op.create_table(
            "grievance_categories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(40), nullable=False, unique=True),
            sa.Column("label_rw", sa.String(120), nullable=False),
            sa.Column("label_en", sa.String(80), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_grievance_categories_code", "grievance_categories", ["code"])
        op.create_index("ix_grievance_categories_label_en", "grievance_categories", ["label_en"])
        if bind.execute(sa.text("SELECT COUNT(*) FROM grievance_categories")).scalar() == 0:
            for index, (code, label_rw, label_en) in enumerate(GRIEVANCE_SEED):
                bind.execute(
                    sa.text(
                        "INSERT INTO grievance_categories (code, label_rw, label_en, sort_order, is_active) "
                        "VALUES (:code, :label_rw, :label_en, :sort_order, TRUE)"
                    ),
                    {"code": code, "label_rw": label_rw, "label_en": label_en, "sort_order": index},
                )

    if "scheme_assets" not in tables:
        op.create_table(
            "scheme_assets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("scheme_id", sa.Integer(), sa.ForeignKey("irrigation_schemes.id"), nullable=True),
            sa.Column("name_rw", sa.String(120), nullable=False),
            sa.Column("name_en", sa.String(120), nullable=False),
            sa.Column("asset_type", sa.String(40), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_scheme_assets_scheme_id", "scheme_assets", ["scheme_id"])
        if bind.execute(sa.text("SELECT COUNT(*) FROM scheme_assets")).scalar() == 0:
            schemes = bind.execute(sa.text("SELECT id, name FROM irrigation_schemes")).fetchall()
            for name_rw, name_en, prefix, asset_type in ASSET_SEED:
                match = next((row.id for row in schemes if str(row.name).startswith(prefix)), None)
                bind.execute(
                    sa.text(
                        "INSERT INTO scheme_assets (scheme_id, name_rw, name_en, asset_type, is_active) "
                        "VALUES (:scheme_id, :name_rw, :name_en, :asset_type, TRUE)"
                    ),
                    {"scheme_id": match, "name_rw": name_rw, "name_en": name_en, "asset_type": asset_type},
                )

    if "bottleneck_baselines" not in tables:
        op.create_table(
            "bottleneck_baselines",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("scheme_id", sa.Integer(), sa.ForeignKey("irrigation_schemes.id"), nullable=False),
            sa.Column("asset_name", sa.String(120), nullable=True),
            sa.Column("category", sa.String(30), nullable=False),
            sa.Column("finding_date", sa.Date(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("source", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_bottleneck_baselines_scheme_id", "bottleneck_baselines", ["scheme_id"])
        op.create_index("ix_bottleneck_baselines_category", "bottleneck_baselines", ["category"])


def downgrade() -> None:
    for table in ("bottleneck_baselines", "scheme_assets", "grievance_categories", "advisory_thresholds"):
        if table in sa.inspect(op.get_bind()).get_table_names():
            op.drop_table(table)
