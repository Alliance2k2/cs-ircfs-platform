"""Initial CS-IRCFS schema.

Revision ID: 20260911_01
Revises:

The baseline creates the tables that no later revision owns. Everything added later
(cases, platform accounts, messaging, the channel tables, account_sectors and
community_feedback_events) is created by its own revision, so `alembic upgrade head`
applies cleanly on a fresh database as well as incrementally.

Frozen in October 2026: this revision used to call Base.metadata.create_all(), so what
it created changed whenever the models changed (and a fresh PostgreSQL failed once a
baseline table referenced a later one). It now spells out every table explicitly, as
the models stood at revision 20261010_16. Later revisions that add the same columns or
tables check before acting, so fresh and upgraded databases end at the same schema.
Databases that already ran this revision are unaffected.
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.types import Text, TypeDecorator

revision = "20260911_01"
down_revision = None
branch_labels = None
depends_on = None


class SpatialGeometry(TypeDecorator):
    """A frozen copy of app.db.models.SpatialGeometry: PostGIS geometry on PostgreSQL, text elsewhere."""

    impl = Text
    cache_ok = True
    spatial_index = False

    def __init__(self, geometry_type: str, srid: int = 4326):
        self.geometry_type = geometry_type
        self.srid = srid
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Geometry(self.geometry_type, srid=self.srid, spatial_index=False))
        return dialect.type_descriptor(Text())


TABLES = ['grievance_categories', 'sectors', 'advice_runs', 'advisory_thresholds', 'cells', 'irrigation_schemes', 'bottleneck_baselines', 'cooperatives', 'scheme_assets', 'field_users', 'citizen_science_logs', 'community_feedback', 'irrigation_climate_logs']


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table('grievance_categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('label_rw', sa.String(length=120), nullable=False),
    sa.Column('label_en', sa.String(length=80), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_grievance_categories_code'), 'grievance_categories', ['code'], unique=True)
    op.create_index(op.f('ix_grievance_categories_label_en'), 'grievance_categories', ['label_en'], unique=False)
    op.create_table('sectors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('boundary', SpatialGeometry("MULTIPOLYGON"), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sectors_name'), 'sectors', ['name'], unique=True)
    op.create_table('advice_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('week_key', sa.String(length=10), nullable=False),
    sa.Column('sector_id', sa.Integer(), nullable=False),
    sa.Column('recipients', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['sector_id'], ['sectors.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('week_key', 'sector_id', name='uq_advice_run_week_sector')
    )
    op.create_index(op.f('ix_advice_runs_sector_id'), 'advice_runs', ['sector_id'], unique=False)
    op.create_index(op.f('ix_advice_runs_week_key'), 'advice_runs', ['week_key'], unique=False)
    op.create_table('advisory_thresholds',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sector_id', sa.Integer(), nullable=False),
    sa.Column('dry_mm', sa.Float(), nullable=False),
    sa.Column('wet_mm', sa.Float(), nullable=False),
    sa.Column('source', sa.String(length=255), nullable=True),
    sa.Column('valid_from', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['sector_id'], ['sectors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_advisory_thresholds_sector_id'), 'advisory_thresholds', ['sector_id'], unique=True)
    op.create_table('cells',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('sector_id', sa.Integer(), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('boundary', SpatialGeometry("MULTIPOLYGON"), nullable=True),
    sa.ForeignKeyConstraint(['sector_id'], ['sectors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cells_name'), 'cells', ['name'], unique=False)
    op.create_index(op.f('ix_cells_sector_id'), 'cells', ['sector_id'], unique=False)
    op.create_table('irrigation_schemes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('implementing_partner', sa.String(length=100), nullable=True),
    sa.Column('hectares_developed', sa.Float(), nullable=True),
    sa.Column('baseline_yield_target_tons', sa.Float(), nullable=True),
    sa.Column('baseline_source', sa.String(length=255), nullable=True),
    sa.Column('sector_id', sa.Integer(), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('boundary', SpatialGeometry("MULTIPOLYGON"), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['sector_id'], ['sectors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_irrigation_schemes_name'), 'irrigation_schemes', ['name'], unique=True)
    op.create_table('bottleneck_baselines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('scheme_id', sa.Integer(), nullable=False),
    sa.Column('asset_name', sa.String(length=120), nullable=True),
    sa.Column('category', sa.String(length=30), nullable=False),
    sa.Column('finding_date', sa.Date(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('source', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['scheme_id'], ['irrigation_schemes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bottleneck_baselines_category'), 'bottleneck_baselines', ['category'], unique=False)
    op.create_index(op.f('ix_bottleneck_baselines_scheme_id'), 'bottleneck_baselines', ['scheme_id'], unique=False)
    op.create_table('cooperatives',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('sector_id', sa.Integer(), nullable=True),
    sa.Column('irrigation_scheme_id', sa.Integer(), nullable=True),
    sa.Column('is_pilot', sa.Boolean(), nullable=False),
    sa.Column('contact_field_user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['irrigation_scheme_id'], ['irrigation_schemes.id'], ),
    sa.ForeignKeyConstraint(['sector_id'], ['sectors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cooperatives_name'), 'cooperatives', ['name'], unique=True)
    op.create_table('scheme_assets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('scheme_id', sa.Integer(), nullable=True),
    sa.Column('name_rw', sa.String(length=120), nullable=False),
    sa.Column('name_en', sa.String(length=120), nullable=False),
    sa.Column('asset_type', sa.String(length=40), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['scheme_id'], ['irrigation_schemes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scheme_assets_scheme_id'), 'scheme_assets', ['scheme_id'], unique=False)
    op.create_table('field_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('phone_number', sa.String(length=20), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=True),
    sa.Column('role', sa.Enum('farmer', 'citizen_science_monitor', 'cooperative_leader', 'district_officer', 'district_planner', 'administrator', name='userrole'), nullable=False),
    sa.Column('cooperative_name', sa.String(length=120), nullable=True),
    sa.Column('cooperative_id', sa.Integer(), nullable=True),
    sa.Column('cell_id', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_data_champion', sa.Boolean(), nullable=False),
    sa.Column('trained_at', sa.Date(), nullable=True),
    sa.Column('training_notes', sa.Text(), nullable=True),
    sa.Column('location', SpatialGeometry("POINT"), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['cell_id'], ['cells.id'], ),
    sa.ForeignKeyConstraint(['cooperative_id'], ['cooperatives.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_field_users_cooperative_id'), 'field_users', ['cooperative_id'], unique=False)
    op.create_index(op.f('ix_field_users_phone_number'), 'field_users', ['phone_number'], unique=True)
    op.create_table('citizen_science_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reporter_id', sa.Integer(), nullable=True),
    sa.Column('scheme_id', sa.Integer(), nullable=True),
    sa.Column('cell_id', sa.Integer(), nullable=True),
    sa.Column('crop_type', sa.String(length=80), nullable=False),
    sa.Column('crop_variety', sa.String(length=80), nullable=True),
    sa.Column('planting_date', sa.Date(), nullable=True),
    sa.Column('expected_harvest_month', sa.Date(), nullable=True),
    sa.Column('expected_harvest_tons', sa.Float(), nullable=True),
    sa.Column('reported_harvest_tons', sa.Float(), nullable=True),
    sa.Column('pest_or_disease', sa.String(length=120), nullable=True),
    sa.Column('severity', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('data_origin', sa.String(length=12), server_default='field', nullable=False),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['cell_id'], ['cells.id'], ),
    sa.ForeignKeyConstraint(['reporter_id'], ['field_users.id'], ),
    sa.ForeignKeyConstraint(['scheme_id'], ['irrigation_schemes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citizen_science_logs_cell_id'), 'citizen_science_logs', ['cell_id'], unique=False)
    op.create_index(op.f('ix_citizen_science_logs_data_origin'), 'citizen_science_logs', ['data_origin'], unique=False)
    op.create_index(op.f('ix_citizen_science_logs_reporter_id'), 'citizen_science_logs', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_citizen_science_logs_scheme_id'), 'citizen_science_logs', ['scheme_id'], unique=False)
    op.create_table('community_feedback',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reporter_id', sa.Integer(), nullable=True),
    sa.Column('scheme_id', sa.Integer(), nullable=True),
    sa.Column('cell_id', sa.Integer(), nullable=True),
    sa.Column('category', sa.String(length=80), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('status', sa.Enum('open', 'triaged', 'assigned', 'in_progress', 'resolved', 'closed', name='reportstatus'), nullable=False),
    sa.Column('assigned_to_field_user_id', sa.Integer(), nullable=True),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('action_taken', sa.Text(), nullable=True),
    sa.Column('data_origin', sa.String(length=12), server_default='field', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['assigned_to_field_user_id'], ['field_users.id'], ),
    sa.ForeignKeyConstraint(['cell_id'], ['cells.id'], ),
    sa.ForeignKeyConstraint(['reporter_id'], ['field_users.id'], ),
    sa.ForeignKeyConstraint(['scheme_id'], ['irrigation_schemes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_community_feedback_assigned_to_field_user_id'), 'community_feedback', ['assigned_to_field_user_id'], unique=False)
    op.create_index(op.f('ix_community_feedback_cell_id'), 'community_feedback', ['cell_id'], unique=False)
    op.create_index(op.f('ix_community_feedback_data_origin'), 'community_feedback', ['data_origin'], unique=False)
    op.create_index(op.f('ix_community_feedback_reporter_id'), 'community_feedback', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_community_feedback_scheme_id'), 'community_feedback', ['scheme_id'], unique=False)
    op.create_table('irrigation_climate_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reporter_id', sa.Integer(), nullable=True),
    sa.Column('scheme_id', sa.Integer(), nullable=True),
    sa.Column('cell_id', sa.Integer(), nullable=True),
    sa.Column('infrastructure_name', sa.String(length=120), nullable=True),
    sa.Column('operational_status', sa.String(length=30), nullable=True),
    sa.Column('bottleneck_category', sa.String(length=30), nullable=True),
    sa.Column('fault_description', sa.Text(), nullable=True),
    sa.Column('rainfall_mm', sa.Float(), nullable=True),
    sa.Column('data_origin', sa.String(length=12), server_default='field', nullable=False),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['cell_id'], ['cells.id'], ),
    sa.ForeignKeyConstraint(['reporter_id'], ['field_users.id'], ),
    sa.ForeignKeyConstraint(['scheme_id'], ['irrigation_schemes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_irrigation_climate_logs_cell_id'), 'irrigation_climate_logs', ['cell_id'], unique=False)
    op.create_index(op.f('ix_irrigation_climate_logs_data_origin'), 'irrigation_climate_logs', ['data_origin'], unique=False)
    op.create_index(op.f('ix_irrigation_climate_logs_reporter_id'), 'irrigation_climate_logs', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_irrigation_climate_logs_scheme_id'), 'irrigation_climate_logs', ['scheme_id'], unique=False)


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
    if op.get_bind().dialect.name == "postgresql":
        sa.Enum(name="reportstatus").drop(op.get_bind(), checkfirst=True)
        sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
