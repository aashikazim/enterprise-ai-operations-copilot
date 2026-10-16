from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Customer, Ticket
from app.api.schemas import (
    TicketCreate, TicketResponse, TicketUpdate
)
from app.auth.dependencies import get_current_user, require_admin
from app.db.models import User

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=TicketResponse, status_code=201)
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    if data.customer_id != user.customer_id:
        raise HTTPException(403, "Access denied")

    ticket = Ticket(**data.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/", response_model=list[TicketResponse])
def list_tickets(
    customer_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if customer_id is not None and customer_id != user.customer_id:
        raise HTTPException(403, "Access denied")

    query = (
        select(Ticket)
        .where(Ticket.customer_id == user.customer_id)
        .order_by(Ticket.id)
    )
    return db.scalars(query).all()


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = db.get(Ticket, ticket_id)

    if not ticket or ticket.customer_id != user.customer_id:
        raise HTTPException(404, "Ticket not found")

    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    ticket = db.get(Ticket, ticket_id)

    if not ticket or ticket.customer_id != user.customer_id:
        raise HTTPException(404, "Ticket not found")

    ticket.status = data.status
    db.commit()
    db.refresh(ticket)
    return ticket


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    ticket = db.get(Ticket, ticket_id)

    if not ticket or ticket.customer_id != user.customer_id:
        raise HTTPException(404, "Ticket not found")

    db.delete(ticket)
    db.commit()