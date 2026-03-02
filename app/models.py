from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def uuid_str() -> str:
    return str(uuid4())


class AssetStatus(str, Enum):
    IN_STOCK = "in_stock"
    ASSIGNED = "assigned"
    CHECKED_OUT = "checked_out"
    IN_REPAIR = "in_repair"
    LOST = "lost"
    RETIRED = "retired"
    PENDING_ENROLLMENT = "pending_enrollment"


class CheckoutType(str, Enum):
    CHECKOUT = "checkout"
    CHECKIN = "checkin"
    TRANSFER = "transfer"
    OFFBOARDING = "offboarding"
    BULK = "bulk"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), default="employee")
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")


class Location(Base, TimestampMixin):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")


class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    po_number: Mapped[str] = mapped_column(String(100), unique=True)
    vendor_id: Mapped[Optional[str]] = mapped_column(ForeignKey("vendors.id"), nullable=True)


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("serial_number", name="uq_asset_serial"),
        UniqueConstraint("asset_tag", name="uq_asset_tag"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    asset_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    status: Mapped[AssetStatus] = mapped_column(SAEnum(AssetStatus), default=AssetStatus.IN_STOCK)
    abm_device_id: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    kandji_device_id: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    location_id: Mapped[Optional[str]] = mapped_column(ForeignKey("locations.id"), nullable=True)
    assigned_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    retired_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    assignments: Mapped[list[Assignment]] = relationship(back_populates="asset")


class Device(Base, TimestampMixin):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), unique=True)
    platform: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    os_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    enrollment_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expected_return_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    state: Mapped[str] = mapped_column(String(32), default="active")

    asset: Mapped[Asset] = relationship(back_populates="assignments")


class CheckoutTransaction(Base, TimestampMixin):
    __tablename__ = "checkout_transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    type: Mapped[CheckoutType] = mapped_column(SAEnum(CheckoutType), nullable=False)
    initiated_by_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    subject_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    asset_id: Mapped[Optional[str]] = mapped_column(ForeignKey("assets.id"), nullable=True)
    location_id: Mapped[Optional[str]] = mapped_column(ForeignKey("locations.id"), nullable=True)
    policy_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    signature_blob_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    condition_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Warranty(Base, TimestampMixin):
    __tablename__ = "warranties"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    provider: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class RepairTicket(Base, TimestampMixin):
    __tablename__ = "repair_tickets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    description: Mapped[str] = mapped_column(Text)
    repair_status: Mapped[str] = mapped_column(String(32), default="open")


class Accessory(Base, TimestampMixin):
    __tablename__ = "accessories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    parent_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    name: Mapped[str] = mapped_column(String(120))
    serial_number: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    is_required_on_return: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="attached")


class ImportJob(Base, TimestampMixin):
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    source: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="success")
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)


class IntegrationConnection(Base, TimestampMixin):
    __tablename__ = "integration_connections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    provider: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="disconnected")
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    event_ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actor_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    object_type: Mapped[str] = mapped_column(String(120))
    object_id: Mapped[str] = mapped_column(String(120))
    before_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
