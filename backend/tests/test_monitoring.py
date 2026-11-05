from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.db.evaluation_job_model import EvaluationJob
from app.db.models import Customer
from app.db.rag_metric_model import RAGMetric
from app.monitoring.queue_summary import queue_summary


NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


def add_job(db, customer_id, status="pending", **values):
    job = EvaluationJob(customer_id=customer_id, status=status, question="PRIVATE QUESTION",
        answer="PRIVATE ANSWER", evidence=[{"content": "PRIVATE DOCUMENT"}],
        created_at=NOW - timedelta(hours=1), available_at=NOW, **values)
    db.add(job)
    return job


def test_summary_math_and_tenant_boundary(db, test_customer):
    other = Customer(name="Other", email="other-monitor@example.com")
    db.add(other)
    db.flush()
    add_job(db, test_customer.id)
    add_job(db, test_customer.id, "running", started_at=NOW - timedelta(minutes=5),
            lease_expires_at=NOW - timedelta(seconds=1), attempts=2)
    add_job(db, test_customer.id, "completed", started_at=NOW - timedelta(seconds=30),
            completed_at=NOW - timedelta(seconds=10),
            result={"claims": [{"verdict": "supported"}, {"verdict": "unsupported"}, {"verdict": "ignored"}]})
    add_job(db, other.id, "failed")
    for n, latency in enumerate([10, 20, 30]):
        db.add(RAGMetric(request_id=f"synthetic-{n}", customer_id=test_customer.id,
            latency_ms=latency, retrieval_ms=1, generation_ms=1, input_tokens=1, output_tokens=1,
            estimated_cost_usd=0, abstained=n == 0, citations_valid=n != 2,
            faithfulness_score=0.5, created_at=NOW - timedelta(minutes=1)))
    db.add(RAGMetric(request_id="foreign", customer_id=other.id, latency_ms=9000,
        retrieval_ms=1, generation_ms=1, input_tokens=1, output_tokens=1,
        estimated_cost_usd=0, abstained=False, citations_valid=True, created_at=NOW))
    db.commit()
    value = queue_summary(db, test_customer.id, now=NOW)
    assert value["jobs"] == {"pending": 1, "running": 1, "completed": 1, "failed": 0}
    assert value["expired_running_leases"] == 1
    assert value["oldest_pending_age_seconds"] == 3600
    assert value["oldest_running_age_seconds"] == 300
    assert value["retries_in_window"] == 1
    assert value["completed_in_window"] == 1
    assert value["average_processing_seconds"] == 20
    assert value["claim_verdicts"] == {"supported": 1, "unsupported": 1, "contradicted": 0}
    metrics = value["rag_metrics"]
    assert metrics["request_count"] == 3
    assert metrics["latency_p50_ms"] == 20
    assert metrics["latency_p95_ms"] == pytest.approx(29)
    assert metrics["abstention_rate"] == pytest.approx(1 / 3)
    assert metrics["citation_failure_rate"] == pytest.approx(1 / 3)
    assert metrics["average_faithfulness"] == .5


def test_empty_summary(db, test_customer):
    value = queue_summary(db, test_customer.id, now=NOW)
    assert sum(value["jobs"].values()) == 0
    assert value["oldest_pending_age_seconds"] is None
    assert value["average_processing_seconds"] is None
    assert value["rag_metrics"]["latency_p95_ms"] is None


def test_summary_window_and_malformed_historical_json(db, test_customer):
    add_job(db, test_customer.id, "completed", completed_at=NOW - timedelta(days=2), result={"claims": [{"verdict": "supported"}]})
    add_job(db, test_customer.id, "completed", completed_at=NOW, result={"claims": "not-an-array"})
    db.commit()
    value = queue_summary(db, test_customer.id, now=NOW)
    assert value["jobs"]["completed"] == 2
    assert value["completed_in_window"] == 1
    assert sum(value["claim_verdicts"].values()) == 0


@pytest.mark.parametrize("path", ["summary", "jobs", "metrics"])
def test_monitoring_requires_admin(client, user_headers, path):
    assert client.get(f"/rag/monitoring/{path}").status_code == 401
    assert client.get(f"/rag/monitoring/{path}", headers=user_headers).status_code == 403


def test_admin_job_pagination_and_private_payloads(client, db, test_customer, admin_headers):
    other = Customer(name="Other", email="other-list@example.com")
    db.add(other)
    db.flush()
    for _ in range(3): add_job(db, test_customer.id)
    add_job(db, other.id)
    db.commit()
    first = client.get("/rag/monitoring/jobs?limit=2&status=pending", headers=admin_headers)
    second = client.get("/rag/monitoring/jobs?limit=2&offset=2", headers=admin_headers)
    assert first.status_code == 200
    assert len(first.json()["items"]) == 2 and len(second.json()["items"]) == 1
    assert first.json()["items"][0]["id"] != second.json()["items"][0]["id"]
    assert "PRIVATE" not in first.text and "evidence" not in first.text
    metrics = client.get("/rag/monitoring/metrics", headers=admin_headers)
    assert metrics.status_code == 200
    assert 'copilot_evaluation_jobs{status="pending"} 3' in metrics.text
    assert "PRIVATE" not in metrics.text and "customer_id" not in metrics.text
    assert client.get("/rag/monitoring/summary", headers=admin_headers).json()["jobs"]["pending"] == 3


@pytest.mark.parametrize("query", ["hours=0", "hours=721"])
def test_summary_window_validation(client, admin_headers, query):
    assert client.get("/rag/monitoring/summary?" + query, headers=admin_headers).status_code == 422


def test_operator_metrics_default_off_and_requires_own_token(client, monkeypatch):
    settings = SimpleNamespace(monitoring_metrics_token=SecretStr(""))
    monkeypatch.setattr("app.api.monitoring.get_settings", lambda: settings)
    assert client.get("/metrics").status_code == 404
    settings.monitoring_metrics_token = SecretStr("synthetic-operator-secret")
    assert client.get("/metrics").status_code == 401
    response = client.get("/metrics", headers={"Authorization": "Bearer synthetic-operator-secret"})
    assert response.status_code == 200
    assert "copilot_rag_enqueue_outcomes_total" in response.text
    assert "synthetic-operator-secret" not in response.text
    assert "customer_id" not in response.text
