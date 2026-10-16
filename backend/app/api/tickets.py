from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Customer, Ticket
from app.api.schemas import (
    TicketCreate, TicketResponse, TicketUpdate
)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=TicketResponse, status_code=201)
def create_ticket(data: TicketCreate, db: Session = Depends(get_db)):
    if not db.get(Customer, data.customer_id):
        raise HTTPException(404, "Customer not found")

    ticket = Ticket(**data.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ticket


@router.get("/", response_model=list[TicketResponse])
def list_tickets(
    customer_id: int | None = None,
    db: Session = Depends(get_db)
):
    query = select(Ticket).order_by(Ticket.id)

    if customer_id is not None:
        query = query.where(Ticket.customer_id == customer_id)

    return db.scalars(query).all()


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db)
):
    ticket = db.get(Ticket, ticket_id)

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    ticket.status = data.status
    db.commit()
    db.refresh(ticket)

    return ticket


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    db.delete(ticket)
    db.commit()