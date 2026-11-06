
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


def record_request_metric(db, request_id, customer_id, result, latency_ms, retrieval_ms, generation_ms):
    """Best-effort aggregates only; never commit/rollback the caller's session.

    Latency excludes this persistence and async-evaluation enqueue transaction.
    Provider wrapper currently returns text only, so usage/cost stay unknown.
    """
    if db is None:
        return
    import logging
    from sqlalchemy.orm import sessionmaker
    try:
        factory = sessionmaker(bind=db.get_bind())
        with factory.begin() as session:
            session.add(RAGMetric(request_id=request_id, customer_id=customer_id,
                latency_ms=latency_ms, retrieval_ms=retrieval_ms, generation_ms=generation_ms,
                input_tokens=None, output_tokens=None, estimated_cost_usd=None,
                abstained=result['abstained'],
                citations_valid=result['citation_validation']['citations_valid']))
    except Exception:
        logging.getLogger(__name__).warning('RAG aggregate persistence failed')
