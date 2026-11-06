from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
import time
import threading
from datetime import timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.evaluation_job_model import EvaluationJob
from app.workers.evaluation_worker import process_next_job
from app.jobs.evaluation_queue import claim_next_job, renew_lease, complete_job, utc_now


@pytest.mark.parametrize("workers", [1, 4])
def test_local_queue_load(db, test_customer, workers):
    db.add_all([EvaluationJob(customer_id=test_customer.id, question="Synthetic load",
        answer="Synthetic answer", evidence=[{"title": "Synthetic", "content": "Synthetic"}]) for _ in range(40)])
    db.commit()
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    evaluator = Mock(return_value={"claims": [], "faithfulness_score": None})
    def drain():
        count = 0
        while process_next_job(factory, None, evaluator):
            count += 1
        return count
    start = perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        counts = list(executor.map(lambda _: drain(), range(workers)))
    elapsed = perf_counter() - start
    rows = db.scalars(select(EvaluationJob)).all()
    assert sum(counts) == len(rows) == evaluator.call_count == 40
    assert all(job.status == "completed" and job.attempts == 1 for job in rows)
    waits = sorted((job.started_at - job.created_at).total_seconds() for job in rows)
    print(f"Synthetic queue n=40 workers={workers} elapsed_s={elapsed:.3f} jobs_s={40/elapsed:.2f} wait_p95_s={waits[37]:.3f}")


def seed(db, customer_id):
    job = EvaluationJob(customer_id=customer_id, question="Synthetic", answer="Synthetic",
                        evidence=[{"title": "Synthetic", "content": "Synthetic"}])
    db.add(job)
    db.commit()
    return job.id


def test_lease_renewal_and_stale_fencing(db, test_customer):
    identifier = seed(db, test_customer.id)
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    with factory() as session:
        attempt = claim_next_job(session).attempts
    with factory() as session:
        assert not renew_lease(session, identifier, attempt + 1)
    with factory() as session:
        assert renew_lease(session, identifier, attempt)
    job = db.get(EvaluationJob, identifier)
    job.lease_expires_at = utc_now() - timedelta(seconds=1)
    db.commit()
    with factory() as session:
        assert not renew_lease(session, identifier, attempt)
    with factory() as session:
        assert not complete_job(session, identifier, attempt, {})
    with factory() as session:
        assert claim_next_job(session).attempts == attempt + 1


def test_heartbeat_keeps_slow_work_claimed(db, test_customer):
    identifier = seed(db, test_customer.id)
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    def slow(**kwargs):
        time.sleep(1.2)
        with factory() as check:
            assert claim_next_job(check) is None
        return {"claims": []}
    assert process_next_job(factory, None, slow, lease_seconds=1, heartbeat_interval_seconds=.1)
    db.expire_all()
    assert db.get(EvaluationJob, identifier).status == "completed"


def test_poison_job_is_terminal_without_repeated_cost(db, test_customer):
    identifier = seed(db, test_customer.id)
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    evaluator = Mock(side_effect=ValueError("PRIVATE bad evidence"))
    assert process_next_job(factory, None, evaluator)
    db.expire_all()
    job = db.get(EvaluationJob, identifier)
    assert job.status == "failed" and job.attempts == 1
    assert job.last_error == "permanent_evaluation_failure"
    assert not process_next_job(factory, None, evaluator)
    assert evaluator.call_count == 1


def test_shutdown_does_not_claim_new_work(monkeypatch):
    from app.workers import evaluation_worker as worker
    stop = threading.Event()
    stop.set()
    claim = Mock()
    monkeypatch.setattr(worker, "make_session_factory", lambda: Mock())
    monkeypatch.setattr(worker, "process_next_job", claim)
    worker.run_worker(stop_event=stop, concurrency=2, client_factory=lambda: None)
    claim.assert_not_called()


def test_offline_worker_never_claims_without_credentials(monkeypatch):
    from app.workers import evaluation_worker as worker
    monkeypatch.setattr(worker.get_settings(), 'openai_api_key', '')
    stop = threading.Event()
    claim, provider = Mock(), Mock()
    monkeypatch.setattr(worker, 'process_next_job', claim)
    monkeypatch.setattr(worker, 'OpenAI', provider)
    thread = threading.Thread(target=worker.run_worker, kwargs={'stop_event': stop})
    thread.start()
    try:
        time.sleep(.05)
        assert thread.is_alive()
        claim.assert_not_called()
        provider.assert_not_called()
    finally:
        stop.set()
        thread.join(timeout=2)
    assert not thread.is_alive()
