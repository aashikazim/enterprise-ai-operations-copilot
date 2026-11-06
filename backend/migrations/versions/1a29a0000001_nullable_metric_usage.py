"""Represent unavailable usage/cost honestly without rewriting old metrics.

Revision ID: 1a29a0000001
Revises: 1a18a0000001
"""
from alembic import op
import sqlalchemy as sa

revision = '1a29a0000001'
down_revision = '1a18a0000001'
branch_labels = None
depends_on = None


def upgrade():
    for name, kind in [('input_tokens', sa.Integer()), ('output_tokens', sa.Integer()),
                       ('estimated_cost_usd', sa.Float())]:
        op.alter_column('rag_metrics', name, existing_type=kind, nullable=True)


def downgrade():
    # Downgrade cannot honestly synthesize usage/cost. PostgreSQL rejects this
    # if null records exist; operators must review/export them before rollback.
    for name, kind in [('input_tokens', sa.Integer()), ('output_tokens', sa.Integer()),
                       ('estimated_cost_usd', sa.Float())]:
        op.alter_column('rag_metrics', name, existing_type=kind, nullable=False)
