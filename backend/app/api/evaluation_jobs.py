
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.evaluation_job_model import EvaluationJob
from app.db.database import get_db
from app.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/rag/evaluations",
    tags=["RAG Evaluations"],
)


class EvaluationJobResponse(BaseModel):
    id: str
    status: str
    attempts: int
    result: dict | None
    created_at: datetime
    completed_at: datetime | None


def find_tenant_job(
    db: Session,
    job_id: str,
    customer_id: int,
) -> EvaluationJob | None:
    return db.execute(
        select(EvaluationJob).where(
            EvaluationJob.id == job_id,
            EvaluationJob.customer_id == customer_id,
        )
    ).scalar_one_or_none()



@router.get(
    "/{job_id}",
    response_model=EvaluationJobResponse,
)
def get_evaluation_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = find_tenant_job(
        db=db,
        job_id=job_id,
        customer_id=current_user.customer_id,
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation job not found",
        )

    return EvaluationJobResponse(
        id=job.id,
        status=job.status,
        attempts=job.attempts,
        result=job.result,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
