"""SQLAlchemy 2.0 models for geography, people, irrigation, field reports, cases, and messaging.

Two clearly separate people systems live here:

* ``FieldUser`` — USSD/SMS callers: farmers, Citizen Science Monitors, cooperative leaders.
* ``PlatformAccount`` — web dashboard staff who sign in with an email and password.
"""
import enum
from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    TypeDecorator,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SpatialGeometry(TypeDecorator):
    """A geometry column that becomes PostGIS on PostgreSQL and TEXT elsewhere.

    GeoAlchemy's DDL hooks inspect this on the mapped column type itself, so the
    spatial index stays off; it can be added once verified spatial data is loaded.
    """

    impl = Text
    cache_ok = True
    spatial_index = False

    def __init__(self, geometry_type: str, srid: int = 4326):
        self.geometry_type = geometry_type
        self.srid = srid
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect is None:
            return Text()
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Geometry(self.geometry_type, srid=self.srid, spatial_index=False))
        return dialect.type_descriptor(Text())


class UserRole(str, enum.Enum):
    farmer = "farmer"
    citizen_science_monitor = "citizen_science_monitor"
    cooperative_leader = "cooperative_leader"
    district_officer = "district_officer"
    district_planner = "district_planner"
    administrator = "administrator"


class ReportStatus(str, enum.Enum):
    open = "open"
    triaged = "triaged"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


# Incident cases wrap one crop or infrastructure report; no other source types exist.
SOURCE_CROP = "crop"
SOURCE_INFRASTRUCTURE = "infrastructure"
SOURCE_TYPES = (SOURCE_CROP, SOURCE_INFRASTRUCTURE)
PRIORITIES = ("critical", "high", "medium")

# Where a field record came from (migration 20261010_16). Dashboards count "field" and
# "import" as evidence, label "demo" as demonstration data and leave "simulator" out.
ORIGIN_FIELD = "field"
ORIGIN_SIMULATOR = "simulator"
ORIGIN_DEMO = "demo"
ORIGIN_IMPORT = "import"
DATA_ORIGINS = (ORIGIN_FIELD, ORIGIN_SIMULATOR, ORIGIN_DEMO, ORIGIN_IMPORT)


def data_origin_column() -> Mapped[str]:
    return mapped_column(String(12), default=ORIGIN_FIELD, server_default=ORIGIN_FIELD, index=True)


class Sector(Base):
    __tablename__ = "sectors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    boundary: Mapped[object | None] = mapped_column(SpatialGeometry("MULTIPOLYGON"))
    cells: Mapped[list["Cell"]] = relationship(back_populates="sector")


class AdviceRun(Base):
    """One sector's automatic irrigation-advice send for one week (WP2).

    The (week_key, sector_id) pair is unique so the weekly scheduler and the cron script
    can never send the same week's advice to the same sector twice, and every automatic
    send stays auditable: how many recipients and how the provider answered.
    """

    __tablename__ = "advice_runs"
    __table_args__ = (UniqueConstraint("week_key", "sector_id", name="uq_advice_run_week_sector"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    week_key: Mapped[str] = mapped_column(String(10), index=True)  # Monday of the week, Africa/Kigali
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id"), index=True)
    recipients: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # sent, partial, dry_run, failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Cell(Base):
    __tablename__ = "cells"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id"), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    boundary: Mapped[object | None] = mapped_column(SpatialGeometry("MULTIPOLYGON"))
    sector: Mapped["Sector"] = relationship(back_populates="cells")


class IrrigationScheme(Base):
    __tablename__ = "irrigation_schemes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    implementing_partner: Mapped[str | None] = mapped_column(String(100))
    hectares_developed: Mapped[float | None] = mapped_column(Float)
    baseline_yield_target_tons: Mapped[float | None] = mapped_column(Float)
    baseline_source: Mapped[str | None] = mapped_column(String(255))
    sector_id: Mapped[int | None] = mapped_column(ForeignKey("sectors.id"))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    boundary: Mapped[object | None] = mapped_column(SpatialGeometry("MULTIPOLYGON"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Cooperative(Base):
    """A farmer cooperative (WP5). Pilot cooperatives host the Data Champion pilot.

    ``contact_field_user_id`` is a plain integer with no foreign key: ``field_users``
    already points at ``cooperatives`` and a second constraint would make the two tables
    mutually dependent (which SQLite's ``create_all`` cannot order). The API validates
    that the contact exists before saving.
    """

    __tablename__ = "cooperatives"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    sector_id: Mapped[int | None] = mapped_column(ForeignKey("sectors.id"))
    irrigation_scheme_id: Mapped[int | None] = mapped_column(ForeignKey("irrigation_schemes.id"))
    is_pilot: Mapped[bool] = mapped_column(Boolean, default=False)
    contact_field_user_id: Mapped[int | None] = mapped_column(Integer)  # validated in the API, no FK (see docstring)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FieldUser(Base):
    """A USSD/SMS caller. Never an account: field users do not sign in to the web."""

    __tablename__ = "field_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.farmer)
    cooperative_name: Mapped[str | None] = mapped_column(String(120))  # legacy free text; superseded by cooperative_id
    cooperative_id: Mapped[int | None] = mapped_column(ForeignKey("cooperatives.id"), index=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Data Champion designation and training record (WP5, Section 8 objective 5).
    is_data_champion: Mapped[bool] = mapped_column(Boolean, default=False)
    trained_at: Mapped[date | None] = mapped_column(Date)
    training_notes: Mapped[str | None] = mapped_column(Text)
    location: Mapped[object | None] = mapped_column(SpatialGeometry("POINT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdvisoryThreshold(Base):
    """Calibrated rainfall thresholds for one sector (WP7, Section 9.2).

    When present, these override DRY_SPELL_THRESHOLD_MM / WET_SPELL_THRESHOLD_MM
    from the environment for that sector. ``source`` records the document or CSV
    the calibration came from; NULL means the value is unverified.
    """

    __tablename__ = "advisory_thresholds"
    id: Mapped[int] = mapped_column(primary_key=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id"), unique=True, index=True)
    dry_mm: Mapped[float] = mapped_column(Float)
    wet_mm: Mapped[float] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(255))
    valid_from: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GrievanceCategory(Base):
    """Grievance categories shown by USSD option 5 and editable in Management (WP7).

    ``label_en`` is what gets stored in ``community_feedback.category``, so it must
    keep matching the historical values unless the district deliberately renames one.
    """

    __tablename__ = "grievance_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    label_rw: Mapped[str] = mapped_column(String(120))
    label_en: Mapped[str] = mapped_column(String(80), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SchemeAsset(Base):
    """The asset inventory behind USSD option 4 (WP7): pump, canal, solar array…

    Seeded from the PADAB and APEFA inventories by migration 20261009_15; the
    district edits it in Management without code changes.
    """

    __tablename__ = "scheme_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int | None] = mapped_column(ForeignKey("irrigation_schemes.id"), index=True)
    name_rw: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    asset_type: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BottleneckBaseline(Base):
    """Historical AfDB evaluation findings imported by scripts/import_bottleneck_baseline.py.

    A category is auto-flagged only above its historical baseline for that scheme,
    and the scheme page shows "above historical baseline" next to it.
    """

    __tablename__ = "bottleneck_baselines"
    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("irrigation_schemes.id"), index=True)
    asset_name: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(30), index=True)
    finding_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Area-level access: an account linked to sectors sees records from those sectors only.
# No rows means the whole district.
account_sectors = Table(
    "account_sectors",
    Base.metadata,
    Column("account_id", ForeignKey("platform_accounts.id", ondelete="CASCADE"), primary_key=True),
    Column("sector_id", ForeignKey("sectors.id", ondelete="CASCADE"), primary_key=True),
)


class PlatformAccount(Base):
    """Web dashboard staff. Never a field user: accounts sign in with an email."""

    __tablename__ = "platform_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)  # the unique constraint is the index
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(256))
    # Stored as VARCHAR(40), as migration 20260929_05 created it (not a database enum type).
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False, length=40), default=UserRole.citizen_science_monitor)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sectors: Mapped[list["Sector"]] = relationship(secondary=account_sectors, order_by="Sector.name")

    @property
    def sector_ids(self) -> list[int]:
        return [sector.id for sector in self.sectors]


class AuthSession(Base):
    """A signed-in browser session. Only a SHA-256 hash of the token is stored."""

    __tablename__ = "auth_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("platform_accounts.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AdvisoryMessage(Base):
    """Every outbound SMS: advisories, auto-replies, local tips, and closing-the-loop blasts."""

    __tablename__ = "advisory_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    language: Mapped[str] = mapped_column(String(10), default="rw")
    message: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(10), default="sms")
    status: Mapped[str] = mapped_column(String(20), default="queued")
    provider_id: Mapped[str | None] = mapped_column(String(120))
    purpose: Mapped[str | None] = mapped_column(String(30), index=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InboundMessage(Base):
    """A USSD step or SMS received from a citizen, and the record it produced.

    ``record_id`` is informational only; it deliberately carries no foreign key so a
    retired source record never blocks an inbound log from being written.
    """

    __tablename__ = "inbound_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    channel: Mapped[str] = mapped_column(String(10))
    session_id: Mapped[str | None] = mapped_column(String(120), index=True)
    text: Mapped[str | None] = mapped_column(Text)
    reply: Mapped[str | None] = mapped_column(Text)
    record_type: Mapped[str | None] = mapped_column(String(40))
    record_id: Mapped[int | None] = mapped_column(Integer)
    data_origin: Mapped[str] = data_origin_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NutritionSurvey(Base):
    """Household Nutrition Tracker: short USSD survey on food access and feeding frequency."""

    __tablename__ = "nutrition_surveys"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("field_users.id"), index=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id"), index=True)
    meals_per_day: Mapped[int] = mapped_column(Integer)
    ate_protein_or_vegetables: Mapped[bool] = mapped_column(Boolean)
    food_sufficient: Mapped[bool] = mapped_column(Boolean)
    stunting_risk_score: Mapped[int] = mapped_column(Integer)
    data_origin: Mapped[str] = data_origin_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IncentiveReward(Base):
    """Airtime micro-bonus earned for regular weather or infrastructure reporting."""

    __tablename__ = "incentive_rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    field_user_id: Mapped[int] = mapped_column(ForeignKey("field_users.id"), index=True)
    phone_number: Mapped[str] = mapped_column(String(20))
    amount_rwf: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    provider_id: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CitizenScienceLog(Base):
    """Crop harvest and pest/disease reports."""

    __tablename__ = "citizen_science_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("field_users.id"), index=True)
    scheme_id: Mapped[int | None] = mapped_column(ForeignKey("irrigation_schemes.id"), index=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id"), index=True)
    crop_type: Mapped[str] = mapped_column(String(80))
    crop_variety: Mapped[str | None] = mapped_column(String(80))
    planting_date: Mapped[date | None] = mapped_column(Date)
    expected_harvest_month: Mapped[date | None] = mapped_column(Date)
    expected_harvest_tons: Mapped[float | None] = mapped_column(Float)
    reported_harvest_tons: Mapped[float | None] = mapped_column(Float)
    pest_or_disease: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    data_origin: Mapped[str] = data_origin_column()
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IrrigationClimateLog(Base):
    """Infrastructure health and rainfall reports."""

    __tablename__ = "irrigation_climate_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("field_users.id"), index=True)
    scheme_id: Mapped[int | None] = mapped_column(ForeignKey("irrigation_schemes.id"), index=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id"), index=True)
    infrastructure_name: Mapped[str | None] = mapped_column(String(120))
    operational_status: Mapped[str | None] = mapped_column(String(30))
    bottleneck_category: Mapped[str | None] = mapped_column(String(30))
    fault_description: Mapped[str | None] = mapped_column(Text)
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    data_origin: Mapped[str] = data_origin_column()
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunityFeedback(Base):
    """Grievances and community reports. ``reporter_id`` is always NULL: grievances are anonymous."""

    __tablename__ = "community_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("field_users.id"), index=True)
    scheme_id: Mapped[int | None] = mapped_column(ForeignKey("irrigation_schemes.id"), index=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id"), index=True)
    category: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.open)
    assigned_to_field_user_id: Mapped[int | None] = mapped_column(ForeignKey("field_users.id"), index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    action_taken: Mapped[str | None] = mapped_column(Text)
    data_origin: Mapped[str] = data_origin_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FeedbackStatusEvent(Base):
    """An immutable audit entry for a community-feedback case transition."""

    __tablename__ = "community_feedback_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    feedback_id: Mapped[int] = mapped_column(ForeignKey("community_feedback.id"), index=True)
    previous_status: Mapped[ReportStatus | None] = mapped_column(Enum(ReportStatus))
    new_status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus))
    action_taken: Mapped[str | None] = mapped_column(Text)
    changed_by_account_id: Mapped[int | None] = mapped_column(ForeignKey("platform_accounts.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IncidentCase(Base):
    """A planner workflow case wrapping one crop or infrastructure report."""

    __tablename__ = "incident_cases"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_incident_source"),
        CheckConstraint("source_type IN ('crop', 'infrastructure')", name="ck_incident_source_type"),
        CheckConstraint("priority IN ('critical', 'high', 'medium')", name="ck_incident_priority"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(30), index=True)
    source_id: Mapped[int] = mapped_column(Integer)
    priority: Mapped[str] = mapped_column(String(12))
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.open)
    assigned_to_account_id: Mapped[int | None] = mapped_column(ForeignKey("platform_accounts.id"))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    action_taken: Mapped[str | None] = mapped_column(Text)
    reporter_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IncidentEvent(Base):
    """An immutable audit entry for an incident-case transition."""

    __tablename__ = "incident_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("incident_cases.id"), index=True)
    previous_status: Mapped[ReportStatus | None] = mapped_column(Enum(ReportStatus))
    new_status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus))
    action_taken: Mapped[str | None] = mapped_column(Text)
    changed_by_account_id: Mapped[int | None] = mapped_column(ForeignKey("platform_accounts.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
