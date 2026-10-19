
from sqlalchemy.orm import Session

from app.db.rag_metric_model import RAGMetric
from app.monitoring.rag_metrics import RAGRequestMetric


def save_rag_metric(
    db: Session,
    metric: RAGRequestMetric,
) -> RAGMetric:
    record = RAGMetric(
        request_id=metric.request_id,
        customer_id=metric.customer_id,
        latency_ms=metric.latency_ms,
        retrieval_ms=metric.retrieval_ms,
        generation_ms=metric.generation_ms,
        input_tokens=metric.input_tokens,
        output_tokens=metric.output_tokens,
        estimated_cost_usd=metric.estimated_cost_usd,
        abstained=metric.abstained,
        citations_valid=metric.citations_valid,
        faithfulness_score=metric.faithfulness_score,
        created_at=metric.created_at,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record
