
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import mean


@dataclass
class RAGRequestMetric:
    request_id: str
    customer_id: int
    latency_ms: float
    retrieval_ms: float
    generation_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    abstained: bool
    citations_valid: bool
    faithfulness_score: float | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def summarize_metrics(
    metrics: list[RAGRequestMetric],
) -> dict:
    if not metrics:
        return {
            "request_count": 0,
            "average_latency_ms": None,
            "abstention_rate": None,
            "citation_failure_rate": None,
            "average_faithfulness": None,
            "total_estimated_cost_usd": 0.0,
        }

    faithfulness_values = [
        item.faithfulness_score
        for item in metrics
        if item.faithfulness_score is not None
    ]

    return {
        "request_count": len(metrics),
        "average_latency_ms": mean(
            item.latency_ms for item in metrics
        ),
        "abstention_rate": mean(
            item.abstained for item in metrics
        ),
        "citation_failure_rate": mean(
            not item.citations_valid for item in metrics
        ),
        "average_faithfulness": (
            mean(faithfulness_values)
            if faithfulness_values
            else None
        ),
        "total_estimated_cost_usd": sum(
            item.estimated_cost_usd
            for item in metrics
        ),
    }
