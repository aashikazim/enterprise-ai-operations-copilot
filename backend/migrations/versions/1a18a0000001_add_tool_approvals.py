"""Add immutable tool proposals and append-only application audit events."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "1a18a0000001"
down_revision = "1a17a0000001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("idempotency_key", sa.String(36), nullable=False),
        sa.Column("tool", sa.String(60), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("customer_id", "requested_by", "idempotency_key", name="uq_approvals_idempotency"))
    op.create_index("ix_approvals_customer_id", "approvals", ["customer_id"])
    op.create_table("approval_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("approval_id", sa.String(36), sa.ForeignKey("approvals.id"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_approval_events_approval_id", "approval_events", ["approval_id"])


def downgrade():
    op.drop_table("approval_events")
    op.drop_table("approvals")
