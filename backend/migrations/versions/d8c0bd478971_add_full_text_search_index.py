"""add full text search index

Revision ID: d8c0bd478971
Revises: 903726799651
Create Date: 2026-10-18 14:28:16.323350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8c0bd478971'
down_revision: Union[str, Sequence[str], None] = '903726799651'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS
        ix_document_chunks_content_fts
        ON document_chunks
        USING GIN (
            to_tsvector('english', content)
        )
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS
        ix_document_chunks_content_fts
    """)
