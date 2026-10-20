
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


def run_worker():
    session_factory = make_session_factory()
    client = OpenAI()

    logger.info("Evaluation worker started")

    while True:
        try:
            # Claim with a fresh session.
            with session_factory() as db:
                expire_exhausted_jobs(db)
                job = claim_next_job(db)

                if job is None:
                    job_data = None
                else:
                    job_data = {
                        "id": job.id,
                        "attempts": job.attempts,
                        "question": job.question,
                        "answer": job.answer,
                        "evidence": job.evidence,
                    }

            if job_data is None:
                time.sleep(3)
                continue

            job_id = job_data["id"]
            attempt = job_data["attempts"]

            logger.info(
                "Evaluating job %s attempt %s",
                job_id,
                attempt,
            )

            try:
                result = evaluate_faithfulness(
                    question=job_data["question"],
                    answer=job_data["answer"],
                    chunks=job_data["evidence"],
                    client=client,
                )

                with session_factory() as db:
                    saved = complete_job(
                        db,
                        job_id=job_id,
                        expected_attempt=attempt,
                        result=result,
                    )

                if saved:
                    logger.info("Job %s completed", job_id)
                else:
                    logger.warning(
                        "Job %s result rejected as stale",
                        job_id,
                    )

            except Exception as exc:
                logger.exception(
                    "Evaluation failed for job %s",
                    job_id,
                )

                with session_factory() as db:
                    fail_job(
                        db,
                        job_id=job_id,
                        expected_attempt=attempt,
                        error=type(exc).__name__,
                    )

        except KeyboardInterrupt:
            logger.info("Worker stopped")
            break

        except Exception:
            logger.exception("Worker loop error")
            time.sleep(5)


if __name__ == "__main__":
    run_worker()
