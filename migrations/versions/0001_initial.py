"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-02-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    role_code = sa.Enum("Admin", "Operator", "Viewer", name="role_code")
    event_item_kind = sa.Enum("object", "group", name="event_item_kind")
    valuation_kind = sa.Enum(
        "accounting", "assessment_act", "price_list", "initial_value_act", "residual_value_statement", name="valuation_kind"
    )
    role_code.create(op.get_bind(), checkfirst=True)
    event_item_kind.create(op.get_bind(), checkfirst=True)
    valuation_kind.create(op.get_bind(), checkfirst=True)

    op.create_table("roles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", role_code, nullable=False, unique=True))

    for tbl in ["users", "units", "services", "nomenclature", "asset_objects", "events", "event_items", "documents", "valuations"]:
        pass

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("short_name", sa.String(128), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("units.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "nomenclature",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("unit_measure", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "asset_objects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("inv_no", sa.String(64)),
        sa.Column("serial_no", sa.String(64)),
        sa.Column("vin", sa.String(64)),
        sa.Column("plate_no", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_asset_inv_no_unique_not_null", "asset_objects", ["inv_no"], unique=True, postgresql_where=sa.text("inv_no IS NOT NULL"))
    op.create_index("ix_asset_vin_unique_not_null", "asset_objects", ["vin"], unique=True, postgresql_where=sa.text("vin IS NOT NULL"))

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "event_units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id"), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("event_id", "unit_id", name="uq_event_unit"),
    )
    op.create_index("ix_event_primary_unit_unique", "event_units", ["event_id"], unique=True, postgresql_where=sa.text("is_primary IS TRUE"))

    op.create_table(
        "event_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", event_item_kind, nullable=False),
        sa.Column("object_id", sa.Integer(), sa.ForeignKey("asset_objects.id")),
        sa.Column("nom_id", sa.Integer(), sa.ForeignKey("nomenclature.id")),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id"), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "(kind = 'object' AND object_id IS NOT NULL AND qty = 1 AND nom_id IS NULL) OR (kind = 'group' AND nom_id IS NOT NULL AND qty > 0 AND object_id IS NULL)",
            name="ck_event_items_kind",
        ),
    )

    op.create_table(
        "doc_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("extension", sa.String(8), nullable=False),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type_id", sa.Integer(), sa.ForeignKey("doc_types.id"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id")),
        sa.Column("doc_no", sa.String(64)),
        sa.Column("doc_date", sa.Date()),
        sa.Column("reg_date", sa.Date()),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "valuations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("kind", valuation_kind, nullable=False),
        sa.Column("value_amount", sa.Numeric(14, 2)),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "valuation_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("valuation_id", sa.Integer(), sa.ForeignKey("valuations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_item_id", sa.Integer(), sa.ForeignKey("event_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applies_qty", sa.Integer(), nullable=False),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("table_name", sa.String(128), nullable=False),
        sa.Column("row_id", sa.String(64), nullable=False),
        sa.Column("details", sa.Text()),
    )

    op.bulk_insert(
        sa.table("roles", sa.column("code", role_code)),
        [{"code": "Admin"}, {"code": "Operator"}, {"code": "Viewer"}],
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("valuation_links")
    op.drop_table("valuations")
    op.drop_table("documents")
    op.drop_table("doc_types")
    op.drop_table("event_items")
    op.drop_index("ix_event_primary_unit_unique", table_name="event_units")
    op.drop_table("event_units")
    op.drop_table("events")
    op.drop_index("ix_asset_vin_unique_not_null", table_name="asset_objects")
    op.drop_index("ix_asset_inv_no_unique_not_null", table_name="asset_objects")
    op.drop_table("asset_objects")
    op.drop_table("nomenclature")
    op.drop_table("services")
    op.drop_table("units")
    op.drop_table("users")
    op.drop_table("roles")
    sa.Enum(name="valuation_kind").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="event_item_kind").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="role_code").drop(op.get_bind(), checkfirst=True)
