from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_customer_ticket_workflow():
    email = f"test-{uuid4().hex}@example.com"

    customer = client.post("/customers/", json={
        "name": "Test Company",
        "email": email
    })
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    ticket = client.post("/tickets/", json={
        "customer_id": customer_id,
        "subject": "API failure",
        "description": "Customer API returned 500",
        "priority": "high"
    })
    assert ticket.status_code == 201

    ticket_id = ticket.json()["id"]

    response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "in_progress"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    response = client.get(
        f"/tickets/?customer_id={customer_id}"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    assert client.delete(f"/tickets/{ticket_id}").status_code == 204