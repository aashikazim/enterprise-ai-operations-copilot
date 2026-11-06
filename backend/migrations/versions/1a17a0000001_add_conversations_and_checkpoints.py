"""Add owner-scoped conversations and PostgreSQL graph checkpoints."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "1a17a0000001"
down_revision = "1a13a0000001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("run_token", sa.String(36)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
    op.create_index("ix_conversations_customer_id", "conversations", ["customer_id"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_table("conversation_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("result", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_conversation_messages_conversation_id", "conversation_messages", ["conversation_id"])
    op.create_table("agent_checkpoints",
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("checkpoint_id", sa.String(80), primary_key=True),
        sa.Column("parent_id", sa.String(80)),
        sa.Column("checkpoint_type", sa.String(40), nullable=False),
        sa.Column("checkpoint_data", sa.LargeBinary(), nullable=False),
        sa.Column("metadata_type", sa.String(40), nullable=False),
        sa.Column("metadata_data", sa.LargeBinary(), nullable=False))
    op.create_table("agent_checkpoint_writes",
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("checkpoint_id", sa.String(80), primary_key=True),
        sa.Column("task_id", sa.String(80), primary_key=True),
        sa.Column("index", sa.Integer(), primary_key=True),
        sa.Column("channel", sa.String(255), nullable=False),
        sa.Column("value_type", sa.String(40), nullable=False),
        sa.Column("value_data", sa.LargeBinary(), nullable=False))


def downgrade():
    op.drop_table("agent_checkpoint_writes")
    op.drop_table("agent_checkpoints")
    op.drop_table("conversation_messages")
    op.drop_table("conversations")
