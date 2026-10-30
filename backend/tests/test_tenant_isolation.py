from app.auth.security import create_access_token, hash_password
from app.db.models import Customer, Ticket, User


def seed_customers(db):
    acme = Customer(
        name="Acme Corporation",
        email="acme@example.com",
    )

    globex = Customer(
        name="Globex Corporation",
        email="globex@example.com",
    )

    db.add_all([acme, globex])
    db.flush()

    admin_a = User(
        email="admin@acme.example",
        hashed_password=hash_password("Password123!"),
        role="admin",
        customer_id=acme.id,
    )

    user_a = User(
        email="user@acme.example",
        hashed_password=hash_password("Password123!"),
        role="user",
        customer_id=acme.id,
    )

    ticket_b = Ticket(
        customer_id=globex.id,
        subject="Globex private ticket",
        description="Confidential customer issue",
        priority="high",
        status="open",
    )

    db.add_all([admin_a, user_a, ticket_b])
    db.commit()

    db.refresh(admin_a)
    db.refresh(user_a)
    db.refresh(ticket_b)

    return admin_a, user_a, ticket_b


def auth_headers(user):
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def test_cannot_read_other_customer_ticket(client, db):
    admin_a, _, ticket_b = seed_customers(db)

    response = client.get(
        f"/tickets/{ticket_b.id}",
        headers=auth_headers(admin_a),
    )

    assert response.status_code == 404


def test_cannot_update_other_customer_ticket(client, db):
    admin_a, _, ticket_b = seed_customers(db)

    response = client.patch(
        f"/tickets/{ticket_b.id}",
        json={"status": "closed"},
        headers=auth_headers(admin_a),
    )

    assert response.status_code == 404


def test_cannot_delete_other_customer_ticket(client, db):
    admin_a, _, ticket_b = seed_customers(db)

    response = client.delete(
        f"/tickets/{ticket_b.id}",
        headers=auth_headers(admin_a),
    )

    assert response.status_code == 404


def test_cannot_list_other_customer_tickets(client, db):
    admin_a, _, ticket_b = seed_customers(db)

    response = client.get(
        "/tickets/",
        headers=auth_headers(admin_a),
    )

    assert response.status_code == 200
    assert all(
        ticket["id"] != ticket_b.id
        for ticket in response.json()
    )


def test_regular_user_cannot_create_ticket(client, db):
    _, user_a, _ = seed_customers(db)

    response = client.post(
        "/tickets/",
        json={
            "customer_id": user_a.customer_id,
            "subject": "Unauthorized ticket",
            "description": "Should not be created",
            "priority": "high",
        },
        headers=auth_headers(user_a),
    )

    assert response.status_code == 403


def test_retrieval_filters_both_document_and_chunk_tenants(db, monkeypatch):
    from unittest.mock import patch
    from app.db.models import Document, DocumentChunk
    from app.services.bm25_retrieval_service import bm25_search
    from app.services.keyword_retrieval_service import keyword_search
    from app.services.hybrid_retrieval_service import hybrid_retrieve, reciprocal_rank_fusion

    customers = [Customer(name=name, email=f"{name}@example.com") for name in ("retrieval-a", "retrieval-b")]
    db.add_all(customers)
    db.flush()
    documents = [Document(title="Synthetic MFA policy", content="MFA", customer_id=c.id) for c in customers]
    db.add_all(documents)
    db.flush()
    chunks = []
    # Include malformed cross-tenant associations to prove both filters apply.
    for index, (document, customer) in enumerate([
        (documents[0], customers[0]), (documents[1], customers[1]),
        (documents[0], customers[1]), (documents[1], customers[0]),
    ]):
        chunk = DocumentChunk(
            document_id=document.id, customer_id=customer.id, chunk_index=index,
            content="MFA recovery", embedding=[1.0] + [0.0] * 383,
        )
        db.add(chunk)
        chunks.append(chunk)
    db.commit()
    monkeypatch.setattr("app.services.retrieval_service.embed_text", lambda _: [1.0] + [0.0] * 383)

    for customer, expected in zip(customers, chunks[:2]):
        for search in (bm25_search, keyword_search):
            assert [r["chunk_id"] for r in search(db, "MFA", customer.id)] == [expected.id]
        with patch(
            "app.services.hybrid_retrieval_service.reciprocal_rank_fusion",
            wraps=reciprocal_rank_fusion,
        ) as fusion:
            results = hybrid_retrieve(db, "MFA", customer.id)
        assert [r["chunk_id"] for r in results] == [expected.id]
        # Verify exclusion before fusion, not just in the returned list.
        for candidates in fusion.call_args.args:
            assert [r["chunk_id"] for r in candidates] == [expected.id]
