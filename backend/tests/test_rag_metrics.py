
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
