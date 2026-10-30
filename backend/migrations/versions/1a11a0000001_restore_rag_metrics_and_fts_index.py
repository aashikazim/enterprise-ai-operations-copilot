"""Create missing RAG metrics and restore the full-text index.

Revision ID: 1a11a0000001
Revises: fa8c76d8e74e
"""

from alembic import op
import sqlalchemy as sa


revision = "1a11a0000001"
down_revision = "fa8c76d8e74e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rag_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("retrieval_ms", sa.Float(), nullable=False),
        sa.Column("generation_ms", sa.Float(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("abstained", sa.Boolean(), nullable=False),
        sa.Column("citations_valid", sa.Boolean(), nullable=False),
        sa.Column("faithfulness_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rag_metrics_request_id", "rag_metrics", ["request_id"], unique=True)
    op.create_index("ix_rag_metrics_customer_id", "rag_metrics", ["customer_id"])
    op.create_index(
        "ix_document_chunks_content_fts",
        "document_chunks",
        [sa.literal_column("to_tsvector('english'::regconfig, content)")],
        postgresql_using="gin",
    )


def downgrade():
    op.drop_index("ix_document_chunks_content_fts", table_name="document_chunks")
    op.drop_index("ix_rag_metrics_customer_id", table_name="rag_metrics")
    op.drop_index("ix_rag_metrics_request_id", table_name="rag_metrics")
    op.drop_table("rag_metrics")
