
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session


from app.db.evaluation_job_model import EvaluationJob
from app.jobs.retry_policy import next_retry_time


def utc_now():
    return datetime.now(timezone.utc)


def enqueue_evaluation(
    db: Session,
    customer_id: int,
    question: str,
    answer: str,
    evidence: list[dict],
) -> EvaluationJob:
    if not question.strip() or not answer.strip():
        raise ValueError("Question and answer are required")

    if not evidence:
        raise ValueError("Evidence is required")

    job = EvaluationJob(
        customer_id=customer_id,
        question=question,
        answer=answer,
        evidence=evidence,
        status="pending",
        available_at=utc_now(),
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def claim_next_job(
    db: Session,
    lease_seconds: int = 600,
) -> EvaluationJob | None:
    now = utc_now()

    with db.begin():
        statement = (
            select(EvaluationJob)
            .where(
                EvaluationJob.attempts
                < EvaluationJob.max_attempts
            )
            .where(
                or_(
                    (
                        (EvaluationJob.status == "pending")
                        & (EvaluationJob.available_at <= now)
                    ),
                    (
                        (EvaluationJob.status == "running")
                        & (
                            EvaluationJob.lease_expires_at
                            < now
                        )
                    ),
                )
            )
            .order_by(
                EvaluationJob.available_at,
                EvaluationJob.created_at,
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        job = db.execute(statement).scalar_one_or_none()

        if job is None:
            return None

        job.status = "running"
        job.attempts += 1
        job.started_at = now
        job.lease_expires_at = now + timedelta(
            seconds=lease_seconds
        )
        job.last_error = None

        db.flush()
        job_id = job.id

    return db.get(EvaluationJob, job_id)


def complete_job(
    db: Session,
    job_id: str,
    expected_attempt: int,
    result: dict,
) -> bool:
    with db.begin():
        job = db.execute(
            select(EvaluationJob)
            .where(EvaluationJob.id == job_id)
            .with_for_update()
        ).scalar_one_or_none()

        if (
            job is None
            or job.status != "running"
            or job.attempts != expected_attempt
        ):
            return False

        job.result = result
        job.status = "completed"
        job.completed_at = utc_now()
        job.lease_expires_at = None
        job.last_error = None

    return True


def fail_job(
    db: Session,
    job_id: str,
    expected_attempt: int,
    error: str,
) -> bool:
    with db.begin():
        job = db.execute(
            select(EvaluationJob)
            .where(EvaluationJob.id == job_id)
            .with_for_update()
        ).scalar_one_or_none()

        if (
            job is None
            or job.status != "running"
            or job.attempts != expected_attempt
        ):
            return False

        job.last_error = error[:2000]
        job.lease_expires_at = None

        if job.attempts >= job.max_attempts:
            job.status = "failed"
            job.completed_at = utc_now()
        else:
            job.status = "pending"
            job.available_at = next_retry_time(
                job.attempts
            )

    return True




def expire_exhausted_jobs(db: Session) -> int:
    now = utc_now()

    with db.begin():
        result = db.execute(
            update(EvaluationJob)
            .where(
                EvaluationJob.status == "running",
                EvaluationJob.lease_expires_at < now,
                EvaluationJob.attempts
                >= EvaluationJob.max_attempts,
            )
            .values(
                status="failed",
                completed_at=now,
                lease_expires_at=None,
                last_error="Worker lease expired after final attempt",
            )
        )

        return result.rowcount
