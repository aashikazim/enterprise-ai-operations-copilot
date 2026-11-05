
import logging
import os
import time
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
)
from app.monitoring.tracing import span, extract_trace_context, configure_tracing
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
    )

    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


def process_next_job(session_factory, client, evaluator=None):
    """Process at most one durable job, with no DB session during inference.

    Return False only for an idle queue. All writes use fresh transactions;
    error details stay outside logs and last_error contains a fixed category.
    """
    evaluator = evaluator or evaluate_faithfulness
    with session_factory() as db:
        expire_exhausted_jobs(db)
        job = claim_next_job(db)
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
        try:
            result = evaluator(
                question=data["question"], answer=data["answer"],
                chunks=data["evidence"], client=client,
            )
        except Exception:
            with session_factory() as db:
                saved = fail_job(db, data["id"], data["attempts"], "evaluation_failed")
            outcome = "retry_or_failure" if saved else "stale_failure"
        else:
            with session_factory() as db:
                saved = complete_job(db, data["id"], data["attempts"], result)
            outcome = "completed" if saved else "stale_result"
        logger.info(
            "evaluation_job job_id=%s attempt=%s outcome=%s duration_ms=%.3f",
            data["id"], data["attempts"], outcome,
            (time.perf_counter() - started) * 1000,
        )
    return True


def run_worker():
    configure_tracing("copilot-worker")
    session_factory = make_session_factory()
    client = OpenAI()
    logger.info("Evaluation worker started")
    while True:
        try:
            if not process_next_job(session_factory, client):
                time.sleep(3)
        except KeyboardInterrupt:
            logger.info("Worker stopped")
            break
        except Exception:
            logger.error("Evaluation worker iteration failed; retrying after delay")
            time.sleep(5)


if __name__ == "__main__":
    run_worker()
