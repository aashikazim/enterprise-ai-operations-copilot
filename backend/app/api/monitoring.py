"""Tenant-admin views plus an explicitly configured operator metrics surface."""
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.db.database import get_db, get_settings
from app.db.evaluation_job_model import EvaluationJob
from app.monitoring.evaluation_metrics import enqueue_snapshot, OUTCOMES
from app.monitoring.queue_summary import queue_summary, prometheus_queue


router = APIRouter(tags=["Monitoring"])


@router.get("/rag/monitoring/summary")
def summary(hours: int = Query(24, ge=1, le=720),
            db: Session = Depends(get_db), user=Depends(require_admin)):
    return queue_summary(db, user.customer_id, hours)


@router.get("/rag/monitoring/jobs")
def jobs(status: str | None = Query(None, pattern="^(pending|running|completed|failed)$"),
         limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
         db: Session = Depends(get_db), user=Depends(require_admin)):
    query = select(EvaluationJob.id, EvaluationJob.status, EvaluationJob.attempts,
                   EvaluationJob.created_at, EvaluationJob.available_at,
                   EvaluationJob.started_at, EvaluationJob.completed_at, EvaluationJob.lease_expires_at
    ).where(EvaluationJob.customer_id == user.customer_id)
    if status:
        query = query.where(EvaluationJob.status == status)
    rows = db.execute(query.order_by(EvaluationJob.created_at.desc(), EvaluationJob.id)
                      .limit(limit).offset(offset)).mappings().all()
    return {"items": [dict(row) for row in rows], "limit": limit, "offset": offset}


@router.get("/rag/monitoring/metrics")
def tenant_metrics(db: Session = Depends(get_db), user=Depends(require_admin)):
    return Response(prometheus_queue(queue_summary(db, user.customer_id)),
                    media_type="text/plain; version=0.0.4")


@router.get("/metrics", include_in_schema=False)
def operator_metrics(authorization: str | None = Header(None)):
    expected = get_settings().monitoring_metrics_token.get_secret_value()
    if not expected:
        raise HTTPException(404, "Not found")
    if not authorization or not secrets.compare_digest(authorization, "Bearer " + expected):
        raise HTTPException(401, "Invalid metrics authorization")
    snapshot = enqueue_snapshot()
    lines = ["# TYPE copilot_rag_enqueue_outcomes_total counter"]
    for outcome in sorted(OUTCOMES):
        lines.append(f'copilot_rag_enqueue_outcomes_total{{outcome="{outcome}"}} {snapshot["counts"].get(outcome, 0)}')
    lines.extend(["# TYPE copilot_rag_enqueue_duration_ms_sum counter",
                  f'copilot_rag_enqueue_duration_ms_sum {snapshot["duration_sum_ms"]}'])
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
