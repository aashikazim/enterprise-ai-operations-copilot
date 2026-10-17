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