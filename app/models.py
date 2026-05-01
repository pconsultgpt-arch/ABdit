from __future__ import annotations

from datetime import datetime, date
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Role(str, Enum):
    SUBSCRIBER = "subscriber"
    SPECIALIST = "specialist"
    WATER_COMPANY = "water_company"
    PROVIDER = "provider"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subscriber: Mapped["Subscriber | None"] = relationship(back_populates="user", uselist=False)
    specialist: Mapped["Specialist | None"] = relationship(back_populates="user", uselist=False)
    provider: Mapped["Provider | None"] = relationship(back_populates="user", uselist=False)
    water_company: Mapped["WaterCompany | None"] = relationship(back_populates="user", uselist=False)


class WaterCompany(Base):
    __tablename__ = "water_companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    region: Mapped[str] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="water_company")
    subscribers: Mapped[list["Subscriber"]] = relationship(back_populates="water_company")


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    water_company_id: Mapped[int] = mapped_column(ForeignKey("water_companies.id"))
    account_number: Mapped[str] = mapped_column(String(64), unique=True)
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(128))
    household_size: Mapped[int] = mapped_column(Integer, default=3)
    has_garden: Mapped[bool] = mapped_column(Boolean, default=False)
    has_pool: Mapped[bool] = mapped_column(Boolean, default=False)
    property_type: Mapped[str] = mapped_column(String(64), default="residential")

    user: Mapped[User] = relationship(back_populates="subscriber")
    water_company: Mapped[WaterCompany] = relationship(back_populates="subscribers")
    readings: Mapped[list["MeterReading"]] = relationship(back_populates="subscriber", cascade="all, delete-orphan")
    bills: Mapped[list["Bill"]] = relationship(back_populates="subscriber", cascade="all, delete-orphan")
    anomalies: Mapped[list["ConsumptionAnomaly"]] = relationship(back_populates="subscriber", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="subscriber", cascade="all, delete-orphan")
    inspections: Mapped[list["InspectionRequest"]] = relationship(back_populates="subscriber", cascade="all, delete-orphan")


class Specialist(Base):
    __tablename__ = "specialists"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    certification_level: Mapped[str] = mapped_column(String(64), default="Certified")
    region: Mapped[str] = mapped_column(String(128))
    rating: Mapped[float] = mapped_column(Float, default=4.5)
    completed_jobs: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(back_populates="specialist")
    inspections: Mapped[list["InspectionRequest"]] = relationship(back_populates="specialist")


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    company_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")

    user: Mapped[User] = relationship(back_populates="provider")
    products: Mapped[list["Product"]] = relationship(back_populates="provider", cascade="all, delete-orphan")


class MeterReading(Base):
    __tablename__ = "meter_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    cubic_meters: Mapped[float] = mapped_column(Float)

    subscriber: Mapped[Subscriber] = relationship(back_populates="readings")


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    cubic_meters: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)

    subscriber: Mapped[Subscriber] = relationship(back_populates="bills")


class ConsumptionAnomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"))
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    severity: Mapped[str] = mapped_column(String(16))  # low / medium / high
    z_score: Mapped[float] = mapped_column(Float)
    peer_ratio: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    subscriber: Mapped[Subscriber] = relationship(back_populates="anomalies")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_id: Mapped[int | None] = mapped_column(ForeignKey("anomalies.id"), nullable=True)

    subscriber: Mapped[Subscriber] = relationship(back_populates="notifications")


class InspectionStatus(str, Enum):
    REQUESTED = "requested"
    ASSIGNED = "assigned"
    REPORT_SUBMITTED = "report_submitted"
    PROPOSAL_SENT = "proposal_sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    INSTALLED = "installed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InspectionRequest(Base):
    __tablename__ = "inspection_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"))
    specialist_id: Mapped[int | None] = mapped_column(ForeignKey("specialists.id"), nullable=True)
    anomaly_id: Mapped[int | None] = mapped_column(ForeignKey("anomalies.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=InspectionStatus.REQUESTED.value)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    subscriber: Mapped[Subscriber] = relationship(back_populates="inspections")
    specialist: Mapped[Specialist | None] = relationship(back_populates="inspections")
    report: Mapped["InspectionReport | None"] = relationship(back_populates="inspection", uselist=False, cascade="all, delete-orphan")
    proposal: Mapped["Proposal | None"] = relationship(back_populates="inspection", uselist=False, cascade="all, delete-orphan")


class InspectionReport(Base):
    __tablename__ = "inspection_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspection_requests.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    plumbing_findings: Mapped[str] = mapped_column(Text, default="")
    irrigation_findings: Mapped[str] = mapped_column(Text, default="")
    leakage_findings: Mapped[str] = mapped_column(Text, default="")
    usage_observations: Mapped[str] = mapped_column(Text, default="")
    estimated_savings_pct: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str] = mapped_column(Text, default="")

    inspection: Mapped[InspectionRequest] = relationship(back_populates="report")


class ProductCategory(str, Enum):
    SMART_IRRIGATION = "smart_irrigation"
    EFFICIENT_FAUCET = "efficient_faucet"
    EFFICIENT_SHOWERHEAD = "efficient_showerhead"
    LEAK_DETECTION = "leak_detection"
    WATER_RECYCLING = "water_recycling"
    SMART_METER = "smart_meter"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[float] = mapped_column(Float)
    install_fee: Mapped[float] = mapped_column(Float, default=0.0)
    expected_savings_pct: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    provider: Mapped[Provider] = relationship(back_populates="products")


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspection_requests.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft / sent / accepted / declined
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    inspection: Mapped[InspectionRequest] = relationship(back_populates="proposal")
    items: Mapped[list["ProposalItem"]] = relationship(back_populates="proposal", cascade="all, delete-orphan")
    installation: Mapped["Installation | None"] = relationship(back_populates="proposal", uselist=False, cascade="all, delete-orphan")


class ProposalItem(Base):
    __tablename__ = "proposal_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("proposals.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float)
    install_fee: Mapped[float] = mapped_column(Float, default=0.0)
    selected: Mapped[bool] = mapped_column(Boolean, default=True)

    proposal: Mapped[Proposal] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class Installation(Base):
    __tablename__ = "installations"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("proposals.id"))
    installed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="scheduled")  # scheduled / installed / verified
    actual_savings_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, default="")

    proposal: Mapped[Proposal] = relationship(back_populates="installation")


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    region: Mapped[str] = mapped_column(String(128), default="")
    expected_savings_pct: Mapped[float] = mapped_column(Float, default=0.0)
    cases_count: Mapped[int] = mapped_column(Integer, default=0)


class TrainingProgram(Base):
    __tablename__ = "training_programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    duration_weeks: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, default="")
    certified_count: Mapped[int] = mapped_column(Integer, default=0)
