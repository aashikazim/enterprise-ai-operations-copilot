from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.dependencies import require_admin
from app.db.database import get_db
from app.db.models import Document, Ticket, User

router = APIRouter(prefix="/admin", tags=["Tenant administration"])


@router.get("/records/{kind}")
def records(kind: Literal["documents", "tickets", "users"],
            limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
            status: Literal["open", "in_progress", "closed"] | None = None,
            db: Session = Depends(get_db), user=Depends(require_admin)):
    if kind == "documents":
        query = select(Document.id, Document.title, Document.created_at).where(Document.customer_id == user.customer_id).order_by(Document.id)
    elif kind == "users":
        query = select(User.id, User.email, User.role, User.is_active).where(User.customer_id == user.customer_id).order_by(User.id)
    else:
        query = select(Ticket.id, Ticket.subject, Ticket.status, Ticket.priority, Ticket.created_at).where(Ticket.customer_id == user.customer_id).order_by(Ticket.id)
        if status: query = query.where(Ticket.status == status)
    values = db.execute(query.limit(limit).offset(offset)).mappings().all()
    return {"items": [dict(value) for value in values], "limit": limit, "offset": offset}
