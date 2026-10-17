def test_create_ticket(client, test_customer, admin_headers):
    response = client.post(
        "/tickets/",
        json={
            "customer_id": test_customer.id,
            "subject": "Payment failed",
            "description": "Subscription payment failed",
            "priority": "high",
        },
        headers=admin_headers,
    )

    assert response.status_code == 201

    ticket = response.json()

    assert ticket["subject"] == "Payment failed"
    assert ticket["customer_id"] == test_customer.id
    assert ticket["status"] == "open"


def test_list_tickets(client, test_customer, admin_headers):
    client.post(
        "/tickets/",
        json={
            "customer_id": test_customer.id,
            "subject": "Login issue",
            "description": "Cannot log in",
            "priority": "medium",
        },
        headers=admin_headers,
    )

    response = client.get(
        "/tickets/",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_update_ticket(client, test_customer, admin_headers):
    created = client.post(
        "/tickets/",
        json={
            "customer_id": test_customer.id,
            "subject": "Update test",
            "description": "Testing status update",
            "priority": "medium",
        },
        headers=admin_headers,
    )

    assert created.status_code == 201
    ticket_id = created.json()["id"]

    response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "closed"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "closed"


def test_delete_ticket(client, test_customer, admin_headers):
    created = client.post(
        "/tickets/",
        json={
            "customer_id": test_customer.id,
            "subject": "Delete test",
            "description": "Testing deletion",
            "priority": "low",
        },
        headers=admin_headers,
    )

    assert created.status_code == 201
    ticket_id = created.json()["id"]

    response = client.delete(
        f"/tickets/{ticket_id}",
        headers=admin_headers,
    )

    assert response.status_code == 204

    get_response = client.get(
        f"/tickets/{ticket_id}",
        headers=admin_headers,
    )

    assert get_response.status_code == 404


def test_regular_user_cannot_create_ticket(
    client, test_customer, user_headers
):
    response = client.post(
        "/tickets/",
        json={
            "customer_id": test_customer.id,
            "subject": "Unauthorized",
            "description": "Regular user test",
            "priority": "high",
        },
        headers=user_headers,
    )

    assert response.status_code == 403


def test_ticket_requires_auth(client):
    response = client.get("/tickets/")

    assert response.status_code == 401