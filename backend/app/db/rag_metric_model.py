
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


class RAGMetric(Base):
    __tablename__ = "rag_metrics"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )

    request_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        index=True,
    )

    latency_ms: Mapped[float] = mapped_column(Float)
    retrieval_ms: Mapped[float] = mapped_column(Float)
    generation_ms: Mapped[float] = mapped_column(Float)

    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    estimated_cost_usd: Mapped[float] = mapped_column(Float)

    abstained: Mapped[bool] = mapped_column(Boolean)
    citations_valid: Mapped[bool] = mapped_column(Boolean)

    faithfulness_score: Mapped[float | None] = (
        mapped_column(Float, nullable=True)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
