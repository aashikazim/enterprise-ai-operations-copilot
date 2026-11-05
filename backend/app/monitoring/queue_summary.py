"""Read-only tenant-filtered operational aggregates, never evaluation payloads."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, func, select

from app.db.evaluation_job_model import EvaluationJob
from app.db.rag_metric_model import RAGMetric


STATUSES = ("pending", "running", "completed", "failed")
VERDICTS = ("supported", "unsupported", "contradicted")


def queue_summary(db, customer_id, hours=24, now=None):
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    scope = [EvaluationJob.customer_id == customer_id]
    counts = dict(db.execute(select(EvaluationJob.status, func.count())
        .where(*scope).group_by(EvaluationJob.status)).all())
    statuses = {status: counts.get(status, 0) for status in STATUSES}
    oldest = db.scalar(select(func.min(EvaluationJob.created_at))
        .where(*scope, EvaluationJob.status == "pending"))
    oldest_running = db.scalar(select(func.min(EvaluationJob.started_at))
        .where(*scope, EvaluationJob.status == "running"))
    expired = db.scalar(select(func.count()).select_from(EvaluationJob).where(
        *scope, EvaluationJob.status == "running", EvaluationJob.lease_expires_at < now))
    retries = db.scalar(select(func.coalesce(func.sum(EvaluationJob.attempts - 1), 0)).where(
        *scope, EvaluationJob.attempts > 1, EvaluationJob.created_at >= since))
    durations = db.execute(select(
        func.count(),
        func.avg(func.extract("epoch", EvaluationJob.completed_at - EvaluationJob.started_at)),
    ).where(*scope, EvaluationJob.status == "completed", EvaluationJob.completed_at >= since)).one()
    # Structured results are untrusted persisted JSON. Expand and aggregate in
    # PostgreSQL rather than materializing raw claims/documents in the API.
    from sqlalchemy import text
    verdict_rows = db.execute(text("""
        SELECT claim->>'verdict' AS verdict, count(*) AS count
        FROM evaluation_jobs AS job
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_typeof(job.result->'claims') = 'array'
                 THEN job.result->'claims' ELSE '[]'::jsonb END
        ) AS claim
        WHERE job.customer_id = :customer_id AND job.status = 'completed'
          AND job.completed_at >= :since
          AND claim->>'verdict' IN ('supported', 'unsupported', 'contradicted')
        GROUP BY claim->>'verdict'
    """), {"customer_id": customer_id, "since": since}).all()
    verdict_counts = dict(verdict_rows)
    metrics = db.execute(select(
        func.count(),
        func.percentile_cont(0.5).within_group(RAGMetric.latency_ms),
        func.percentile_cont(0.95).within_group(RAGMetric.latency_ms),
        func.avg(RAGMetric.abstained.cast(Integer)),
        func.avg((~RAGMetric.citations_valid).cast(Integer)),
        func.avg(RAGMetric.faithfulness_score),
    ).where(RAGMetric.customer_id == customer_id, RAGMetric.created_at >= since)).one()
    return {
        "window_hours": hours, "generated_at": now,
        "jobs": statuses, "expired_running_leases": expired,
        "oldest_pending_age_seconds": max(0, (now - oldest).total_seconds()) if oldest else None,
        "oldest_running_age_seconds": max(0, (now - oldest_running).total_seconds()) if oldest_running else None,
        "retries_in_window": int(retries), "completed_in_window": durations[0],
        "average_processing_seconds": float(durations[1]) if durations[1] is not None else None,
        "throughput_jobs_per_hour": durations[0] / hours,
        "claim_verdicts": {verdict: verdict_counts.get(verdict, 0) for verdict in VERDICTS},
        "rag_metrics": {
            "request_count": metrics[0], "latency_p50_ms": metrics[1], "latency_p95_ms": metrics[2],
            "abstention_rate": float(metrics[3]) if metrics[3] is not None else None,
            "citation_failure_rate": float(metrics[4]) if metrics[4] is not None else None,
            "average_faithfulness": metrics[5],
        },
    }


def prometheus_queue(summary):
    lines = ["# HELP copilot_evaluation_jobs Current jobs by status.", "# TYPE copilot_evaluation_jobs gauge"]
    for status, count in summary["jobs"].items():
        lines.append(f'copilot_evaluation_jobs{{status="{status}"}} {count}')
    for key in ("expired_running_leases", "oldest_pending_age_seconds", "oldest_running_age_seconds",
                "retries_in_window", "completed_in_window", "average_processing_seconds", "throughput_jobs_per_hour"):
        value = summary[key]
        if value is not None:
            lines.extend([f"# TYPE copilot_evaluation_{key} gauge", f"copilot_evaluation_{key} {value}"])
    return "\n".join(lines) + "\n"
