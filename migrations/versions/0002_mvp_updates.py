"""mvp schema updates

Revision ID: 0002_mvp_updates
Revises: 0001_initial
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_mvp_updates"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    asset_state = sa.Enum("n/o", "on_balance", "off_balance", "written_off", name="asset_state")
    engine_type = sa.Enum("word", "excel", name="engine_type")
    asset_state.create(op.get_bind(), checkfirst=True)
    engine_type.create(op.get_bind(), checkfirst=True)

    op.add_column("event_items", sa.Column("state", asset_state, nullable=True))
    op.add_column("valuations", sa.Column("date_effective", sa.Date(), nullable=True))
    op.alter_column("valuations", "value_amount", new_column_name="value_uah")

    op.add_column("doc_types", sa.Column("engine_type", engine_type, nullable=True))
    op.add_column("doc_types", sa.Column("template_path", sa.String(length=512), nullable=True))
    op.execute("UPDATE doc_types SET engine_type='word' WHERE engine_type IS NULL")
    op.execute("UPDATE doc_types SET template_path = code || '.' || extension WHERE template_path IS NULL")
    op.alter_column("doc_types", "engine_type", nullable=False)
    op.alter_column("doc_types", "template_path", nullable=False)

    op.add_column("audit_log", sa.Column("diff_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_log", "diff_json")
    op.drop_column("doc_types", "template_path")
    op.drop_column("doc_types", "engine_type")
    op.alter_column("valuations", "value_uah", new_column_name="value_amount")
    op.drop_column("valuations", "date_effective")
    op.drop_column("event_items", "state")
    sa.Enum(name="engine_type").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="asset_state").drop(op.get_bind(), checkfirst=False)
