from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from statistics import median
from time import perf_counter

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.database import Settings
from app.db.evaluation_job_model import EvaluationJob
from app.db.models import Customer, Document, DocumentChunk
from app.monitoring.evaluation_metrics import enqueue_snapshot
from app.services import evaluation_submission as submission
from app.services.rag_service import answer_question, build_rag_result, ABSTENTION_MESSAGE
from app.workers.evaluation_worker import process_next_job
from app.jobs.evaluation_queue import claim_next_job, complete_job, utc_now


@pytest.fixture
def enabled(monkeypatch):
    settings = SimpleNamespace(rag_eval_enabled=True, rag_eval_sample_rate=1.0)
    monkeypatch.setattr(submission, "get_settings", lambda: settings)
    return settings


@pytest.fixture
def evidence(db, test_customer):
    document = Document(title="Synthetic MFA policy", content="Synthetic policy", customer_id=test_customer.id)
    db.add(document)
    db.flush()
    chunks = [DocumentChunk(
        document_id=document.id, customer_id=test_customer.id, chunk_index=i,
        content=f"Synthetic MFA requirement {i}", embedding=[1.0] + [0.0] * 383,
    ) for i in range(2)]
    db.add_all(chunks)
    db.commit()
    return [{"chunk_id": c.id, "document_id": document.id, "title": document.title,
             "chunk_index": c.chunk_index, "content": c.content, "similarity": 1.0} for c in reversed(chunks)]


@pytest.mark.parametrize("value", [-0.1, 1.1, "nan", "inf", True, "bad"])
def test_settings_reject_invalid_sample_rate(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="postgresql://localhost/test", jwt_secret_key="dummy",
                 rag_eval_sample_rate=value)


@pytest.mark.parametrize("value", [1, "yes", "on", "invalid"])
def test_settings_reject_non_boolean_enabled(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="postgresql://localhost/test", jwt_secret_key="dummy",
                 rag_eval_enabled=value)


def test_settings_parse_env(monkeypatch):
    monkeypatch.setenv("RAG_EVAL_ENABLED", "true")
    monkeypatch.setenv("RAG_EVAL_SAMPLE_RATE", "0.25")
    settings = Settings(_env_file=None)
    assert settings.rag_eval_enabled is True and settings.rag_eval_sample_rate == 0.25


def test_sampling_boundaries_and_stable_buckets():
    identifiers = [f"request-{n}" for n in range(100)]
    assert not any(submission.sampled(i, 0) for i in identifiers)
    assert all(submission.sampled(i, 1) for i in identifiers)
    selected = [submission.sampled(i, .5) for i in identifiers]
    assert selected == [submission.sampled(i, .5) for i in identifiers]
    assert any(selected) and not all(selected)


@pytest.mark.parametrize("reason", ["disabled", "not_sampled", "abstained", "empty_evidence", "invalid_citations"])
def test_skip_without_session(enabled, reason):
    db = Mock()
    result = {"answer": "Synthetic answer", "abstained": False,
              "citation_validation": {"citations_valid": True}}
    chunks = [{"chunk_id": 1}]
    if reason == "disabled": enabled.rag_eval_enabled = False
    if reason == "not_sampled": enabled.rag_eval_sample_rate = 0
    if reason == "abstained": result["abstained"] = True
    if reason == "empty_evidence": chunks = []
    if reason == "invalid_citations": result["citation_validation"]["citations_valid"] = False
    assert submission.submit_sampled_evaluation(
        db, question="Synthetic question", result=result, chunks=chunks, customer_id=1, request_id="request"
    ) == reason
    db.get_bind.assert_not_called()


def test_evidence_order_snapshot_and_tenant(db, test_customer, evidence):
    converted = submission.verified_evidence(db, evidence, test_customer.id)
    assert [c["chunk_id"] for c in converted] == [c["chunk_id"] for c in evidence]
    assert [c["source_id"] for c in converted] == [1, 2]
    assert converted[0]["content"] == evidence[0]["content"]
    assert submission.verified_evidence(db, evidence, test_customer.id + 1) is None
    assert submission.verified_evidence(db, [evidence[0], evidence[0]], test_customer.id) is None
    assert submission.verified_evidence(db, [{**evidence[0], "content": "changed"}], test_customer.id) is None


def test_document_and_chunk_tenant_both_required(db, test_customer, evidence):
    other = Customer(name="Other synthetic tenant", email="other-synthetic@example.com")
    db.add(other)
    db.flush()
    chunk = db.get(DocumentChunk, evidence[0]["chunk_id"])
    chunk.customer_id = other.id
    db.commit()
    assert submission.verified_evidence(db, evidence[:1], test_customer.id) is None
    assert submission.verified_evidence(db, evidence[:1], other.id) is None


def test_enqueue_failure_preserves_request_transaction(db, test_customer, evidence, enabled, monkeypatch, caplog):
    customer_id = test_customer.id
    pending = Customer(name="Uncommitted synthetic tenant", email="uncommitted@example.com")
    db.add(pending)
    def broken(*args, **kwargs):
        raise RuntimeError("private question/document/password must not appear")
    monkeypatch.setattr(submission, "enqueue_evaluation", broken)
    result = build_rag_result("MFA [Source 1].", evidence)
    assert submission.submit_sampled_evaluation(
        db, question="private question", result=result, chunks=evidence,
        customer_id=customer_id, request_id="opaque-id",
    ) == "enqueue_failed"
    assert pending in db.new
    assert "private question" not in caplog.text and "password" not in caplog.text
    db.commit()
    assert pending.id is not None


def test_no_inline_evaluator_and_api_worker_roundtrip(
    client, db, test_customer, user_headers, evidence, enabled, monkeypatch,
):
    monkeypatch.setattr("app.services.rag_service.retrieve_rag_context", lambda **kwargs: evidence)
    monkeypatch.setattr("app.services.rag_service.generate_answer", lambda **kwargs: "MFA [Source 1].")
    inline = Mock(side_effect=AssertionError("Evaluator called inline"))
    monkeypatch.setattr("app.services.faithfulness_service.evaluate_faithfulness", inline)
    response = client.post("/rag/ask", headers=user_headers, json={"question": "Synthetic MFA question"})
    assert response.status_code == 200
    assert response.json() == build_rag_result("MFA [Source 1].", evidence)
    inline.assert_not_called()
    jobs = db.scalars(select(EvaluationJob)).all()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.customer_id == test_customer.id and job.status == "pending"
    assert [c["chunk_id"] for c in job.evidence] == [c["chunk_id"] for c in evidence]
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    evaluator = Mock(return_value={"faithfulness_score": 1.0, "claims": []})
    assert process_next_job(factory, object(), evaluator)
    db.expire_all()
    assert db.get(EvaluationJob, job.id).status == "completed"
    evaluator.assert_called_once()
    assert evaluator.call_args.kwargs["chunks"] == job.evidence
    status = client.get(f"/rag/evaluations/{job.id}", headers=user_headers)
    assert status.status_code == 200 and status.json()["result"]["faithfulness_score"] == 1.0
    assert not process_next_job(factory, object(), evaluator)


def test_request_session_not_committed_on_success(db, test_customer, evidence, enabled):
    customer_id = test_customer.id
    pending = Customer(name="Pending synthetic tenant", email="pending@example.com")
    db.add(pending)
    result = build_rag_result("MFA [Source 1].", evidence)
    assert submission.submit_sampled_evaluation(
        db, question="Synthetic question", result=result, chunks=evidence,
        customer_id=customer_id, request_id="opaque-id",
    ) == "enqueued"
    assert pending in db.new
    db.rollback()
    assert db.scalar(select(EvaluationJob.id)) is not None


def test_worker_retry_and_expired_attempt_fencing(db, test_customer, evidence, enabled):
    result = build_rag_result("MFA [Source 1].", evidence)
    submission.submit_sampled_evaluation(db, question="Synthetic", result=result, chunks=evidence,
                                        customer_id=test_customer.id, request_id="opaque-id")
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    broken = Mock(side_effect=RuntimeError("Never persist this private error"))
    assert process_next_job(factory, None, broken)
    job = db.scalar(select(EvaluationJob))
    assert job.status == "pending" and job.attempts == 1
    assert job.available_at > utc_now() and job.last_error == "evaluation_failed"
    job.available_at = utc_now() - timedelta(seconds=1)
    db.commit()
    with factory() as claim_db:
        attempt = claim_next_job(claim_db, lease_seconds=-1).attempts
    with factory() as claim_db:
        reclaimed = claim_next_job(claim_db)
        assert reclaimed.attempts == attempt + 1
    with factory() as update_db:
        assert not complete_job(update_db, job.id, attempt, {"stale": True})
    with factory() as update_db:
        assert complete_job(update_db, job.id, attempt + 1, {"faithfulness_score": 1.0})


def test_generation_failure_never_enqueues(db, test_customer, enabled, monkeypatch):
    monkeypatch.setattr("app.services.rag_service.retrieve_rag_context", lambda **kwargs: [{"content": "x", "title": "x", "document_id": 1, "chunk_index": 0}])
    monkeypatch.setattr("app.services.rag_service.generate_answer", Mock(side_effect=RuntimeError("provider unavailable")))
    with pytest.raises(RuntimeError):
        answer_question(db, "Synthetic", test_customer.id)
    assert db.scalar(select(EvaluationJob.id)) is None


def test_foreign_evidence_rejected_without_queue_write(db, test_customer, evidence, enabled):
    result = build_rag_result("MFA [Source 1].", evidence)
    assert submission.submit_sampled_evaluation(db, question="Synthetic", result=result, chunks=evidence,
        customer_id=test_customer.id + 1, request_id="opaque-id") == "invalid_evidence"
    assert db.scalar(select(EvaluationJob.id)) is None


def test_telemetry_has_fixed_safe_keys():
    snapshot = enqueue_snapshot()
    assert set(snapshot["counts"]) <= {"disabled", "not_sampled", "abstained", "empty_evidence",
        "invalid_citations", "invalid_evidence", "enqueued", "enqueue_failed"}
    assert snapshot["duration_sum_ms"] >= 0


def test_exhausted_worker_lease_becomes_terminal(db, test_customer, evidence, enabled):
    result = build_rag_result("MFA [Source 1].", evidence)
    submission.submit_sampled_evaluation(db, question="Synthetic", result=result, chunks=evidence,
                                        customer_id=test_customer.id, request_id="opaque-id")
    job = db.scalar(select(EvaluationJob))
    job.status = "running"
    job.attempts = job.max_attempts
    job.lease_expires_at = utc_now() - timedelta(seconds=1)
    db.commit()
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    evaluator = Mock()
    assert not process_next_job(factory, None, evaluator)
    db.expire_all()
    assert db.get(EvaluationJob, job.id).status == "failed"
    evaluator.assert_not_called()


def test_local_enqueue_overhead(db, test_customer, evidence, enabled):
    """Small reproducible DB microbenchmark; not a model/API load benchmark."""
    customer_id = test_customer.id
    result = build_rag_result("MFA [Source 1].", evidence)
    durations = []
    for n in range(20):
        start = perf_counter()
        assert submission.submit_sampled_evaluation(
            db, question="Synthetic benchmark", result=result, chunks=evidence,
            customer_id=customer_id, request_id=f"benchmark-{n}",
        ) == "enqueued"
        durations.append((perf_counter() - start) * 1000)
    print(f"Local enqueue: n=20 p50_ms={median(durations):.3f} p95_ms={sorted(durations)[18]:.3f}")
