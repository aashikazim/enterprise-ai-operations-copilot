from app.auth.security import create_access_token, hash_password
from app.db.models import Customer, User


def create_admin(db):
    customer = Customer(
        name="Test Company",
        email="testcompany@example.com",
    )
    db.add(customer)
    db.flush()

    admin = User(
        email="admin@testcompany.example",
        hashed_password=hash_password("Password123!"),
        role="admin",
        customer_id=customer.id,
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    return admin


def test_invitation_can_only_be_used_once(client, db):
    admin = create_admin(db)

    headers = {
        "Authorization": (
            f"Bearer {create_access_token(admin.id)}"
        )
    }

    response = client.post(
        "/auth/invitations/",
        json={"email": "newuser@example.com"},
        headers=headers,
    )

    assert response.status_code == 201

    token = response.json()["token"]

    first = client.post(
        "/auth/invitations/accept",
        json={
            "token": token,
            "password": "Password123!",
        },
    )

    assert first.status_code == 201
    assert first.json()["role"] == "user"
    assert first.json()["customer_id"] == admin.customer_id

    second = client.post(
        "/auth/invitations/accept",
        json={
            "token": token,
            "password": "Password123!",
        },
    )

    assert second.status_code == 400


def test_public_registration_is_disabled(client, db):
    response = client.post(
        "/auth/register",
        json={
            "email": "anyone@example.com",
            "password": "Password123!",
            "customer_id": 1,
        },
    )

    assert response.status_code == 404


def test_invitation_requires_admin(client, db):
    response = client.post(
        "/auth/invitations/",
        json={"email": "someone@example.com"},
    )

    assert response.status_code == 401