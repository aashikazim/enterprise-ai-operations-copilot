from datetime import timedelta
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, func

from app.db.models import Ticket, Customer, User
from app.db.approval_models import Approval, ApprovalEvent
from app.db.conversation_models import now
from app.auth.security import create_access_token, hash_password
from sqlalchemy.orm import sessionmaker
from app.services.approval_service import transition


@pytest.fixture
def ticket(db, test_customer):
    value = Ticket(customer_id=test_customer.id, subject="Synthetic", description="Synthetic", status="open")
    db.add(value)
    db.commit()
    return value


def request(client, headers, ticket_id, key=None):
    return client.post("/approvals", headers=headers, json={"ticket_id": ticket_id, "status": "closed", "idempotency_key": key or str(uuid4())})


def test_no_write_before_approval_and_execution(client, db, user_headers, admin_headers, ticket):
    response = request(client, user_headers, ticket.id)
    assert response.status_code == 201
    identifier = response.json()["id"]
    denied = client.post(f"/approvals/{identifier}/execute", headers=admin_headers)
    assert denied.status_code == 409
    db.refresh(ticket)
    assert ticket.status == "open"
    approved = client.post(f"/approvals/{identifier}/approve", headers=admin_headers)
    assert approved.json()["status"] == "approved"
    db.refresh(ticket)
    assert ticket.status == "open"
    execution = client.post(f"/approvals/{identifier}/execute", headers=admin_headers)
    assert execution.status_code == 200 and execution.json()["status"] == "executed"
    db.refresh(ticket)
    assert ticket.status == "closed"
    replay = client.post(f"/approvals/{identifier}/execute", headers=admin_headers)
    assert replay.json()["status"] == "executed"
    assert db.scalar(select(func.count()).select_from(ApprovalEvent).where(ApprovalEvent.event == "executed")) == 1


def test_proposal_idempotency_and_rejection(client, db, user_headers, admin_headers, ticket):
    key = str(uuid4())
    first = request(client, user_headers, ticket.id, key).json()
    second = request(client, user_headers, ticket.id, key).json()
    assert first["id"] == second["id"]
    assert db.scalar(select(func.count()).select_from(Approval)) == 1
    response = client.post(f"/approvals/{first['id']}/reject", headers=admin_headers)
    assert response.json()["status"] == "rejected"
    response = client.post(f"/approvals/{first['id']}/execute", headers=admin_headers)
    assert response.status_code == 409


def test_roles_and_cross_tenant_denial(client, db, user_headers, admin_headers, ticket):
    identifier = request(client, user_headers, ticket.id).json()["id"]
    response = client.post(f"/approvals/{identifier}/approve", headers=user_headers)
    assert response.status_code == 403
    other = Customer(name="Foreign", email="approvals-foreign@example.com")
    db.add(other)
    db.flush()
    admin = User(email="foreign-approver@example.com", customer_id=other.id,
                 hashed_password=hash_password("SyntheticPassword!"), role="admin")
    db.add(admin)
    db.commit()
    foreign_headers = {"Authorization": "Bearer " + create_access_token(admin.id)}
    for action in ["approve", "reject", "execute"]:
        response = client.post(f"/approvals/{identifier}/{action}", headers=foreign_headers)
        assert response.status_code == 404
    response = request(client, foreign_headers, ticket.id)
    assert response.status_code == 404
    response = client.get(f"/approvals/{identifier}", headers=foreign_headers)
    assert response.status_code == 404


@pytest.mark.parametrize("fault", ["expired", "changed_ticket", "tampered_args", "revoked_approver"])
def test_execution_preconditions(client, db, user_headers, admin_headers, test_admin, ticket, fault):
    identifier = request(client, user_headers, ticket.id).json()["id"]
    response = client.post(f"/approvals/{identifier}/approve", headers=admin_headers)
    assert response.status_code == 200
    approval = db.get(Approval, identifier)
    if fault == "expired": approval.expires_at = now() - timedelta(seconds=1)
    if fault == "changed_ticket": ticket.status = "in_progress"
    if fault == "tampered_args": approval.payload = {**approval.payload, "status": "in_progress"}
    if fault == "revoked_approver": test_admin.role = "user"
    db.commit()
    response = client.post(f"/approvals/{identifier}/execute", headers=admin_headers)
    assert response.status_code in {403, 409}
    db.refresh(ticket)
    assert ticket.status != "closed"


def test_agent_creates_durable_proposal_only(client, db, user_headers, ticket):
    response = client.post("/agents/run", headers=user_headers, json={"question": f"close ticket {ticket.id}"})
    assert response.status_code == 200
    assert response.json()["intent"] == "approval_required"
    proposal = response.json()["approvals"][0]
    assert db.get(Approval, proposal["id"]).status == "requested"
    db.refresh(ticket)
    assert ticket.status == "open"


def test_expired_decision_is_persisted(client, db, user_headers, admin_headers, ticket):
    identifier = request(client, user_headers, ticket.id).json()["id"]
    value = db.get(Approval, identifier)
    value.expires_at = now() - timedelta(seconds=1)
    db.commit()
    response = client.post(f"/approvals/{identifier}/approve", headers=admin_headers)
    assert response.status_code == 409
    db.refresh(value)
    assert value.status == "expired"


def test_concurrent_execution_mutates_once(client, db, user_headers, admin_headers, test_admin, ticket):
    identifier = request(client, user_headers, ticket.id).json()["id"]
    response = client.post(f"/approvals/{identifier}/approve", headers=admin_headers)
    assert response.status_code == 200
    factory = sessionmaker(bind=db.get_bind())
    admin_id = test_admin.id
    def execute():
        with factory() as session:
            return transition(session, session.get(User, admin_id), identifier, "execute")["status"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: execute(), range(2))) == ["executed", "executed"]
    assert db.scalar(select(func.count()).select_from(ApprovalEvent).where(ApprovalEvent.event == "executed")) == 1


def test_revoked_original_approver_blocks_other_admin(client, db, user_headers, admin_headers, test_admin, ticket):
    identifier = request(client, user_headers, ticket.id).json()["id"]
    response = client.post(f"/approvals/{identifier}/approve", headers=admin_headers)
    assert response.status_code == 200
    other = User(customer_id=test_admin.customer_id, role="admin", email="second-approver@example.com",
                 hashed_password=hash_password("SyntheticPassword!"))
    db.add(other)
    test_admin.role = "user"
    db.commit()
    headers = {"Authorization": "Bearer " + create_access_token(other.id)}
    response = client.post(f"/approvals/{identifier}/execute", headers=headers)
    assert response.status_code == 409
    db.refresh(ticket)
    assert ticket.status == "open"
