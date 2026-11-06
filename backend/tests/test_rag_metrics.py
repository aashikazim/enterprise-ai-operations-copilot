
import pytest

from app.monitoring.rag_metrics import (
    RAGRequestMetric,
    summarize_metrics,
)


def test_metrics_aggregation():
    records = [
        RAGRequestMetric(
            request_id="req-1",
            customer_id=1,
            latency_ms=100,
            retrieval_ms=20,
            generation_ms=80,
            input_tokens=100,
            output_tokens=50,
            estimated_cost_usd=0.001,
            abstained=False,
            citations_valid=True,
            faithfulness_score=1.0,
        ),
        RAGRequestMetric(
            request_id="req-2",
            customer_id=1,
            latency_ms=200,
            retrieval_ms=50,
            generation_ms=150,
            input_tokens=200,
            output_tokens=100,
            estimated_cost_usd=0.002,
            abstained=True,
            citations_valid=False,
            faithfulness_score=0.5,
        ),
    ]

    summary = summarize_metrics(records)

    assert summary["request_count"] == 2
    assert summary["average_latency_ms"] == 150
    assert summary["abstention_rate"] == 0.5
    assert summary["citation_failure_rate"] == 0.5
    assert summary["average_faithfulness"] == 0.75
    assert summary["total_estimated_cost_usd"] == pytest.approx(
        0.003
    )


def test_empty_metrics():
    summary = summarize_metrics([])

    assert summary["request_count"] == 0
    assert summary["average_faithfulness"] is None


def test_metric_persistence(db, test_customer):
    from app.monitoring.metric_repository import save_rag_metric

    metric = RAGRequestMetric(
        request_id="metric-persistence-test",
        customer_id=test_customer.id,
        latency_ms=100,
        retrieval_ms=20,
        generation_ms=80,
        input_tokens=100,
        output_tokens=50,
        estimated_cost_usd=0.001,
        abstained=False,
        citations_valid=True,
    )
    record = save_rag_metric(db, metric)
    assert record.id is not None
    assert record.customer_id == test_customer.id
    assert record.request_id == metric.request_id
    assert record.faithfulness_score is None


def test_live_request_metrics_and_worker_join(client, db, test_customer, user_headers, monkeypatch):
    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker
    from tests.test_bm25_retrieval import seed_chunks
    from app.db.rag_metric_model import RAGMetric
    from app.db.database import get_settings
    from app.workers.evaluation_worker import process_next_job
    chunks = seed_chunks(db, test_customer.id, ['Synthetic MFA evidence'])
    chunk = chunks[0]
    evidence = [{'chunk_id': chunk.id, 'document_id': chunk.document_id, 'title': 'Synthetic retrieval policy',
                 'chunk_index': 0, 'content': chunk.content, 'similarity': 1.0}]
    monkeypatch.setattr('app.services.rag_service.retrieve_rag_context', lambda **kwargs: evidence)
    monkeypatch.setattr('app.services.rag_service.generate_answer', lambda **kwargs: 'Synthetic MFA [Source 1].')
    monkeypatch.setattr(get_settings(), 'rag_eval_enabled', True)
    monkeypatch.setattr(get_settings(), 'rag_eval_sample_rate', 1.0)
    response = client.post('/rag/ask', headers=user_headers, json={'question': 'Synthetic'})
    assert response.status_code == 200
    record = db.scalar(select(RAGMetric))
    assert record.customer_id == test_customer.id
    assert record.latency_ms >= record.retrieval_ms >= 0
    assert record.generation_ms >= 0
    assert record.input_tokens is record.output_tokens is record.estimated_cost_usd is None
    assert record.faithfulness_score is None
    assert process_next_job(sessionmaker(bind=db.get_bind()), None,
                            lambda **kwargs: {'claims': [], 'faithfulness_score': .75})
    db.refresh(record)
    assert record.faithfulness_score == .75
    summary = client.get('/rag/monitoring/summary', headers=user_headers)
    assert summary.status_code == 403


def test_metric_failure_preserves_unrelated_request_work(db, test_customer, monkeypatch, caplog):
    from app.monitoring import metric_repository as repository
    from app.db.models import Customer
    customer_id = test_customer.id
    pending = Customer(name='Pending synthetic', email='metric-pending@example.test')
    db.add(pending)
    class Broken:
        def __init__(self, **kwargs):
            raise RuntimeError('PRIVATE payload')
    monkeypatch.setattr(repository, 'RAGMetric', Broken)
    repository.record_request_metric(db, 'opaque', customer_id,
        {'abstained': True, 'citation_validation': {'citations_valid': True}}, 1, 1, 0)
    assert pending in db.new and 'PRIVATE' not in caplog.text
    db.commit()
    assert pending.id is not None


def test_worker_metric_join_never_crosses_tenant(db, test_customer):
    from sqlalchemy.orm import sessionmaker
    from app.db.models import Customer
    from app.db.rag_metric_model import RAGMetric
    from app.db.evaluation_job_model import EvaluationJob
    from app.workers.evaluation_worker import process_next_job
    other = Customer(name='Foreign metrics', email='metrics-other@example.test')
    db.add(other)
    db.flush()
    metric = RAGMetric(request_id='synthetic-conflicting-id', customer_id=other.id,
        latency_ms=1, retrieval_ms=1, generation_ms=0, abstained=False, citations_valid=True)
    db.add_all([metric, EvaluationJob(customer_id=test_customer.id, request_id=metric.request_id,
        question='Synthetic', answer='Synthetic', evidence=[{'title':'Synthetic','content':'Synthetic'}])])
    db.commit()
    assert process_next_job(sessionmaker(bind=db.get_bind()), None,
                            lambda **kwargs: {'faithfulness_score': 1.0})
    db.refresh(metric)
    assert metric.faithfulness_score is None


def test_metric_write_overhead(db, test_customer):
    from statistics import median
    from time import perf_counter
    from sqlalchemy import select, func
    from app.db.rag_metric_model import RAGMetric
    from app.monitoring.metric_repository import record_request_metric
    identifier = test_customer.id
    durations = []
    for index in range(20):
        started = perf_counter()
        record_request_metric(db, f'synthetic-overhead-{index}', identifier,
            {'abstained': True, 'citation_validation': {'citations_valid': True}}, 1, 1, 0)
        durations.append((perf_counter()-started)*1000)
    assert db.scalar(select(func.count()).select_from(RAGMetric)) == 20
    print(f'Independent metric writes n=20 p50_ms={median(durations):.3f} p95_ms={sorted(durations)[18]:.3f}')
