from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import get_current_user, require_admin
from app.db.database import get_db
from app.db.approval_models import Approval, ApprovalEvent
from app.services.approval_service import propose, transition, scoped, view, ApprovalMissing, ApprovalConflict


router = APIRouter(prefix="/approvals", tags=["Approvals"])


class ProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket_id: int = Field(gt=0, strict=True)
    status: Literal["open", "in_progress", "closed"]
    idempotency_key: UUID


@router.post("", status_code=201)
def create(data: ProposalRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return propose(db, user, data.ticket_id, data.status, str(data.idempotency_key))
    except ApprovalMissing:
        raise HTTPException(404, "Ticket not found") from None
    except ApprovalConflict:
        raise HTTPException(409, "Idempotency key already used") from None
    except IntegrityError:
        raise HTTPException(409, "Concurrent proposal already reserved; reload before retrying") from None
    except PermissionError:
        raise HTTPException(403, "Approval authorization denied") from None


@router.get("")
def listing(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
            status: Literal["requested", "approved", "rejected", "expired", "executed", "failed"] | None = None,
            db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = select(Approval).where(Approval.customer_id == user.customer_id)
    if user.role != "admin":
        query = query.where(Approval.requested_by == user.id)
    if status:
        query = query.where(Approval.status == status)
    return {"items": [view(v) for v in db.scalars(query.order_by(Approval.created_at.desc(), Approval.id).limit(limit).offset(offset))]}


@router.get("/{identifier}")
def detail(identifier: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        value = scoped(db, identifier, user)
        events = db.execute(select(ApprovalEvent.event, ApprovalEvent.created_at)
            .where(ApprovalEvent.approval_id == value.id).order_by(ApprovalEvent.created_at, ApprovalEvent.id)).mappings().all()
        return {**view(value), "events": [dict(row) for row in events]}
    except ApprovalMissing:
        raise HTTPException(404, "Approval not found") from None


@router.post("/{identifier}/{action}")
def action(identifier: str, action: Literal["approve", "reject", "execute"],
           db: Session = Depends(get_db), user=Depends(require_admin)):
    try:
        return transition(db, user, identifier, action)
    except ApprovalMissing:
        raise HTTPException(404, "Approval not found") from None
    except ApprovalConflict:
        raise HTTPException(409, "Approval transition or precondition denied") from None
    except PermissionError:
        raise HTTPException(403, "Approval authorization denied") from None
