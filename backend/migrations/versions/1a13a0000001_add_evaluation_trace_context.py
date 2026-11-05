"""Persist safe correlation across evaluation queue boundaries."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "1a13a0000001"
down_revision = "1a11a0000001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("evaluation_jobs", sa.Column("request_id", sa.String(36), nullable=True))
    op.add_column("evaluation_jobs", sa.Column("trace_context", JSONB(), nullable=True))
    op.create_unique_constraint("uq_evaluation_jobs_request_id", "evaluation_jobs", ["request_id"])


def downgrade():
    op.drop_constraint("uq_evaluation_jobs_request_id", "evaluation_jobs", type_="unique")
    op.drop_column("evaluation_jobs", "trace_context")
    op.drop_column("evaluation_jobs", "request_id")
