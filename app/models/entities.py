from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RoleCode(str, enum.Enum):
    ADMIN = "Admin"
    OPERATOR = "Operator"
    VIEWER = "Viewer"


class EventItemKind(str, enum.Enum):
    OBJECT = "object"
    GROUP = "group"


class AssetState(str, enum.Enum):
    N_O = "n/o"
    ON_BALANCE = "on_balance"
    OFF_BALANCE = "off_balance"
    WRITTEN_OFF = "written_off"


class ValuationKind(str, enum.Enum):
    ACCOUNTING = "accounting"
    ASSESSMENT_ACT = "assessment_act"
    PRICE_LIST = "price_list"
    INITIAL_VALUE_ACT = "initial_value_act"
    RESIDUAL_VALUE_STATEMENT = "residual_value_statement"


class EngineType(str, enum.Enum):
    WORD = "word"
    EXCEL = "excel"


class TimestampVersionMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[RoleCode] = mapped_column(Enum(RoleCode, name="role_code"), unique=True, nullable=False)


class User(Base, TimestampVersionMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[Role] = relationship()


class Unit(Base, TimestampVersionMixin):
    __tablename__ = "units"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    short_name: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"))


class Service(Base, TimestampVersionMixin):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class Nomenclature(Base, TimestampVersionMixin):
    __tablename__ = "nomenclature"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_measure: Mapped[str] = mapped_column(String(32), nullable=False)


class AssetObject(Base, TimestampVersionMixin):
    __tablename__ = "asset_objects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    inv_no: Mapped[str | None] = mapped_column(String(64))
    serial_no: Mapped[str | None] = mapped_column(String(64))
    vin: Mapped[str | None] = mapped_column(String(64))
    plate_no: Mapped[str | None] = mapped_column(String(32))


class Event(Base, TimestampVersionMixin):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    __mapper_args__ = {"version_id_col": row_version}


class EventUnit(Base):
    __tablename__ = "event_units"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (UniqueConstraint("event_id", "unit_id", name="uq_event_unit"),)


class EventItem(Base, TimestampVersionMixin):
    __tablename__ = "event_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[EventItemKind] = mapped_column(Enum(EventItemKind, name="event_item_kind"), nullable=False)
    state: Mapped[AssetState | None] = mapped_column(Enum(AssetState, name="asset_state"))
    object_id: Mapped[int | None] = mapped_column(ForeignKey("asset_objects.id"))
    nom_id: Mapped[int | None] = mapped_column(ForeignKey("nomenclature.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    note: Mapped[str | None] = mapped_column(Text)
    __mapper_args__ = {"version_id_col": row_version}

    __table_args__ = (
        CheckConstraint(
            "(kind = 'object' AND object_id IS NOT NULL AND qty = 1 AND nom_id IS NULL) OR "
            "(kind = 'group' AND nom_id IS NOT NULL AND qty > 0 AND object_id IS NULL)",
            name="ck_event_items_kind",
        ),
    )


class DocType(Base):
    __tablename__ = "doc_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    engine_type: Mapped[EngineType] = mapped_column(Enum(EngineType, name="engine_type"), nullable=False, default=EngineType.WORD)
    template_path: Mapped[str] = mapped_column(String(512), nullable=False)
    extension: Mapped[str] = mapped_column(String(8), nullable=False)


class Document(Base, TimestampVersionMixin):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    doc_type_id: Mapped[int] = mapped_column(ForeignKey("doc_types.id"), nullable=False)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"))
    doc_no: Mapped[str | None] = mapped_column(String(64))
    doc_date: Mapped[date | None] = mapped_column(Date)
    reg_date: Mapped[date | None] = mapped_column(Date)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class Valuation(Base, TimestampVersionMixin):
    __tablename__ = "valuations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    kind: Mapped[ValuationKind] = mapped_column(Enum(ValuationKind, name="valuation_kind"), nullable=False)
    value_uah: Mapped[float | None] = mapped_column(Numeric(14, 2))
    date_effective: Mapped[date | None] = mapped_column(Date)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))


class ValuationLink(Base):
    __tablename__ = "valuation_links"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    valuation_id: Mapped[int] = mapped_column(ForeignKey("valuations.id", ondelete="CASCADE"), nullable=False)
    event_item_id: Mapped[int] = mapped_column(ForeignKey("event_items.id", ondelete="CASCADE"), nullable=False)
    applies_qty: Mapped[int] = mapped_column(Integer, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    table_name: Mapped[str] = mapped_column(String(128), nullable=False)
    row_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    diff_json: Mapped[str | None] = mapped_column(Text)


Index("ix_asset_inv_no_unique_not_null", AssetObject.inv_no, unique=True, postgresql_where=AssetObject.inv_no.is_not(None))
Index("ix_asset_vin_unique_not_null", AssetObject.vin, unique=True, postgresql_where=AssetObject.vin.is_not(None))
Index("ix_event_primary_unit_unique", EventUnit.event_id, unique=True, postgresql_where=EventUnit.is_primary.is_(True))
