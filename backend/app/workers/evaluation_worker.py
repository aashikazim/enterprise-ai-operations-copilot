
import logging
import os
import time
import signal
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dotenv import load_dotenv
# Load environment variables from backend/.env
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.jobs.evaluation_queue import (
    claim_next_job,
    complete_job,
    fail_job,
    expire_exhausted_jobs,
    renew_lease,
)
from app.monitoring.tracing import span, extract_trace_context, configure_tracing
from app.db.database import get_settings
from app.services.faithfulness_service import (
    evaluate_faithfulness,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)


def make_session_factory():
    database_url = os.environ["DATABASE_URL"]

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=max(5, 2 * get_settings().evaluation_worker_concurrency),
    )

    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


def process_next_job(session_factory, client, evaluator=None, *, lease_seconds=600, heartbeat_interval_seconds=60):
    """Process at most one durable job, with no DB session during inference.

    Return False only for an idle queue. All writes use fresh transactions;
    error details stay outside logs and last_error contains a fixed category.
    """
    evaluator = evaluator or evaluate_faithfulness
    with session_factory() as db:
        expire_exhausted_jobs(db)
        job = claim_next_job(db, lease_seconds=lease_seconds)
        if job is None:
            return False
        data = {
            "id": job.id, "attempts": job.attempts, "question": job.question,
            "answer": job.answer, "evidence": job.evidence,
            "trace_context": job.trace_context, "created_at": job.created_at,
        }

    from datetime import datetime, timezone
    with span("evaluation.worker", context=extract_trace_context(data["trace_context"]), **{
        "job.id": data["id"], "job.attempt": data["attempts"],
        "queue.wait_seconds": max(0, (datetime.now(timezone.utc) - data["created_at"]).total_seconds()),
    }):
        started = time.perf_counter()
        heartbeat_stop, lease_lost = threading.Event(), threading.Event()
        def heartbeat():
            while not heartbeat_stop.wait(min(heartbeat_interval_seconds, lease_seconds / 3)):
                try:
                    with session_factory() as db:
                        if not renew_lease(db, data["id"], data["attempts"], lease_seconds):
                            lease_lost.set()
                            return
                except Exception:
                    lease_lost.set()
                    logger.error("Evaluation lease renewal failed")
                    return
        renewal = threading.Thread(target=heartbeat, daemon=True)
        renewal.start()
        try:
            try:
                result = evaluator(
                    question=data["question"], answer=data["answer"],
                    chunks=data["evidence"], client=client,
                )
            except Exception as error:
                if lease_lost.is_set():
                    outcome = "lease_lost"
                else:
                    with session_factory() as db:
                        permanent = isinstance(error, (ValueError, TypeError)) or type(error).__name__ in {
                            "AuthenticationError", "PermissionDeniedError", "BadRequestError",
                        }
                        saved = fail_job(db, data["id"], data["attempts"],
                            "permanent_evaluation_failure" if permanent else "evaluation_failed", permanent=permanent)
                    outcome = "retry_or_failure" if saved else "stale_failure"
            else:
                if lease_lost.is_set():
                    outcome = "lease_lost"
                else:
                    with session_factory() as db:
                        saved = complete_job(db, data["id"], data["attempts"], result)
                    outcome = "completed" if saved else "stale_result"
        finally:
            heartbeat_stop.set()
            renewal.join(timeout=5)
        logger.info(
            "evaluation_job job_id=%s attempt=%s outcome=%s duration_ms=%.3f",
            data["id"], data["attempts"], outcome,
            (time.perf_counter() - started) * 1000,
        )
    return True


def run_worker(stop_event=None, concurrency=None, client_factory=None):
    configure_tracing("copilot-worker")
    settings = get_settings()
    session_factory = make_session_factory()
    stop = stop_event or threading.Event()
    count = concurrency if concurrency is not None else settings.evaluation_worker_concurrency
    if not 1 <= count <= 8:
        raise ValueError("Worker concurrency must be 1..8")
    previous_handlers = {}
    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[signum] = signal.signal(signum, lambda *_: stop.set())
    def consume():
        if client_factory is None and not settings.openai_api_key:
            logger.warning("Evaluation worker waiting: provider credentials not configured")
            # Do not claim/fail durable jobs in an offline developer deployment.
            # Restart the worker after configuring credentials.
            stop.wait()
            return
        client = (client_factory or (lambda: OpenAI(
            api_key=settings.openai_api_key, timeout=60, max_retries=0,
        )))()
        while not stop.is_set():
            try:
                if not process_next_job(session_factory, client, lease_seconds=settings.evaluation_lease_seconds):
                    stop.wait(3)
            except Exception:
                logger.error("Evaluation worker iteration failed; retrying after delay")
                stop.wait(5)
    logger.info("Evaluation worker started concurrency=%s", count)
    try:
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(consume) for _ in range(count)]
            for future in futures:
                future.result()
    finally:
        stop.set()
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        logger.info("Evaluation worker stopped")


if __name__ == "__main__":
    run_worker()
