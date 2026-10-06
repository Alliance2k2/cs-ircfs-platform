import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, TypeDecorator, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry


class SpatialGeometry(TypeDecorator):
    impl = Text
    cache_ok = True
    # GeoAlchemy's DDL hooks inspect this on the mapped column type itself.
    # Indexes can be added explicitly after verified spatial data is loaded.
    spatial_index = False

    def __init__(self, geometry_type: str, srid: int = 4326):
        self.geometry_type = geometry_type
        self.srid = srid
        super().__init__()

    def load_dialect_impl(self, dialect):
        # GeoAlchemy also inspects mapped columns before a dialect is available.
        if dialect is None:
            return Text()
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Geometry(self.geometry_type, srid=self.srid, spatial_index=False))
        return dialect.type_descriptor(Text())

from app.db.base import Base


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


class Sector(Base):
    __tablename__ = "sectors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    boundary: Mapped[object | None] = mapped_column(SpatialGeometry("MULTIPOLYGON"))
    cells: Mapped[list["Cell"]] = relationship(back_populates="sector")


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


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(256))
    full_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.farmer)
    cooperative_name: Mapped[str | None] = mapped_column(String(120))
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    location: Mapped[object | None] = mapped_column(SpatialGeometry("POINT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlatformAccount(Base):
    __tablename__ = "platform_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.citizen_science_monitor)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AuthSession(Base):
    """A signed-in browser session. Only a SHA-256 hash of the bearer token is stored."""

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
    """A USSD step or SMS received from a citizen, and the record it produced."""

    __tablename__ = "inbound_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    channel: Mapped[str] = mapped_column(String(10))
    session_id: Mapped[str | None] = mapped_column(String(120))
    text: Mapped[str | None] = mapped_column(Text)
    reply: Mapped[str | None] = mapped_column(Text)
    record_type: Mapped[str | None] = mapped_column(String(40))
    record_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NutritionSurvey(Base):
    """Household Nutrition Tracker: short USSD survey on food access and feeding frequency."""

    __tablename__ = "nutrition_surveys"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id"), index=True)
    meals_per_day: Mapped[int] = mapped_column(Integer)
    ate_protein_or_vegetables: Mapped[bool] = mapped_column(Boolean)
    food_sufficient: Mapped[bool] = mapped_column(Boolean)
    stunting_risk_score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IncentiveReward(Base):
    """Airtime micro-bonus earned for regular weather or infrastructure reporting."""

    __tablename__ = "incentive_rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    phone_number: Mapped[str] = mapped_column(String(20))
    amount_rwf: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    provider_id: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Farm(Base):
    __tablename__ = "farms"
    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    boundary: Mapped[object] = mapped_column(SpatialGeometry("MULTIPOLYGON"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CitizenScienceLog(Base):
    __tablename__ = "citizen_science_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    scheme_id: Mapped[int | None] = mapped_column(ForeignKey("irrigation_schemes.id"), index=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id"), index=True)
    crop_type: Mapped[str] = mapped_column(String(80))
    planting_date: Mapped[date | None] = mapped_column(Date)
    expected_harvest_tons: Mapped[float | None] = mapped_column(Float)
    reported_harvest_tons: Mapped[float | None] = mapped_column(Float)
    pest_or_disease: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IrrigationClimateLog(Base):
    __tablename__ = "irrigation_climate_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    scheme_id: Mapped[int | None] = mapped_column(ForeignKey("irrigation_schemes.id"), index=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id"), index=True)
    infrastructure_name: Mapped[str | None] = mapped_column(String(120))
    operational_status: Mapped[str | None] = mapped_column(String(30))
    bottleneck_category: Mapped[str | None] = mapped_column(String(30))
    fault_description: Mapped[str | None] = mapped_column(Text)
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunityFeedback(Base):
    __tablename__ = "community_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    scheme_id: Mapped[int | None] = mapped_column(ForeignKey("irrigation_schemes.id"), index=True)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id"), index=True)
    category: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.open)
    assigned_to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    action_taken: Mapped[str | None] = mapped_column(Text)
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
    changed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IncidentCase(Base):
    """A planner workflow for actionable crop and infrastructure reports."""

    __tablename__ = "incident_cases"
    __table_args__ = (UniqueConstraint("source_type", "source_id", name="uq_incident_source"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(30), index=True)
    source_id: Mapped[int] = mapped_column(Integer)
    priority: Mapped[str] = mapped_column(String(12))
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.open)
    assigned_to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    action_taken: Mapped[str | None] = mapped_column(Text)
    reporter_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IncidentEvent(Base):
    __tablename__ = "incident_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("incident_cases.id"), index=True)
    previous_status: Mapped[ReportStatus | None] = mapped_column(Enum(ReportStatus))
    new_status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus))
    action_taken: Mapped[str | None] = mapped_column(Text)
    changed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
