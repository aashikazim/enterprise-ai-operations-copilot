"""Immutable ticket proposals; approved local DB writes execute atomically once."""
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.approval_models import Approval, ApprovalEvent
from app.db.models import User, Ticket
from app.db.conversation_models import now


class ApprovalMissing(LookupError):
    pass


class ApprovalConflict(RuntimeError):
    pass


def digest(customer_id, requested_by, tool, payload):
    return hashlib.sha256(json.dumps([customer_id, requested_by, tool, payload], sort_keys=True).encode()).hexdigest()


def view(value):
    return {"id": value.id, "tool": value.tool, "payload": value.payload, "status": value.status,
            "created_at": value.created_at, "expires_at": value.expires_at}


def active_user(db, identity, admin=False):
    value = db.get(User, identity[0])
    if not value or not value.is_active or value.customer_id != identity[1] or (admin and value.role != "admin"):
        raise PermissionError("Approval authorization denied")
    return value


def propose(db, user, ticket_id, status, idempotency_key):
    if status not in {"open", "in_progress", "closed"} or type(ticket_id) is not int or ticket_id < 1:
        raise ValueError("Invalid ticket action")
    identity = user.id, user.customer_id
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    with factory.begin() as session:
        active_user(session, identity)
        existing = session.scalar(select(Approval).where(Approval.customer_id == identity[1],
            Approval.requested_by == identity[0], Approval.idempotency_key == idempotency_key))
        if existing:
            if existing.payload["ticket_id"] != ticket_id or existing.payload["status"] != status:
                raise ApprovalConflict("Idempotency key already used")
            return view(existing)
        ticket = session.scalar(select(Ticket).where(Ticket.id == ticket_id, Ticket.customer_id == identity[1]))
        if ticket is None:
            raise ApprovalMissing("Ticket not found")
        payload = {"ticket_id": ticket.id, "status": status, "expected_status": ticket.status}
        proposal = Approval(customer_id=identity[1], requested_by=identity[0], idempotency_key=idempotency_key,
            tool="tickets.update_status", payload=payload,
            payload_digest=digest(identity[1], identity[0], "tickets.update_status", payload))
        session.add(proposal)
        session.flush()
        session.add(ApprovalEvent(approval_id=proposal.id, actor_id=identity[0], event="requested"))
        return view(proposal)


def scoped(db, identifier, user, lock=False):
    statement = select(Approval).where(Approval.id == identifier, Approval.customer_id == user.customer_id)
    if user.role != "admin":
        statement = statement.where(Approval.requested_by == user.id)
    if lock:
        statement = statement.with_for_update()
    value = db.scalar(statement)
    if value is None:
        raise ApprovalMissing("Approval not found")
    return value


def transition(db, user, identifier, action):
    if action not in {"approve", "reject", "execute"}:
        raise ValueError("Unknown approval action")
    identity = user.id, user.customer_id
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    error = None
    with factory.begin() as session:
        actor = active_user(session, identity, admin=True)
        value = scoped(session, identifier, actor, lock=True)
        if value.status in {"requested", "approved"} and value.expires_at <= now():
            value.status, error = "expired", "Approval expired"
            event = "expired"
        elif action in {"approve", "reject"}:
            if value.status != "requested":
                raise ApprovalConflict("Approval already decided")
            value.status = "approved" if action == "approve" else "rejected"
            value.approved_by = actor.id if action == "approve" else None
            event = value.status
        elif value.status == "executed":
            return view(value)  # idempotent execution replay, no second mutation/event
        elif value.status != "approved":
            raise ApprovalConflict("Explicit human approval required")
        else:
            approver = session.get(User, value.approved_by)
            valid = (approver is not None and approver.is_active and approver.role == "admin"
                     and approver.customer_id == value.customer_id)
            valid = valid and value.tool == "tickets.update_status" and value.payload_digest == digest(
                value.customer_id, value.requested_by, value.tool, value.payload)
            ticket = session.scalar(select(Ticket).where(Ticket.id == value.payload.get("ticket_id"),
                Ticket.customer_id == actor.customer_id).with_for_update()) if valid else None
            if not valid or ticket is None or ticket.status != value.payload.get("expected_status"):
                value.status, event, error = "failed", "precondition_failed", "Approval precondition failed"
            else:
                ticket.status = value.payload["status"]
                value.status, event = "executed", "executed"
        session.add(ApprovalEvent(approval_id=value.id, actor_id=actor.id, event=event))
        result = view(value)
    if error:
        raise ApprovalConflict(error)
    return result
