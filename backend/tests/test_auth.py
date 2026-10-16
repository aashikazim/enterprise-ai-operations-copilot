from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_protected_endpoint_requires_login():
    response = client.get("/tickets/")
    assert response.status_code == 401


def test_invalid_login():
    response = client.post(
        "/auth/login",
        data={
            "username": "unknown@example.com",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401


def test_invalid_token():
    response = client.get(
        "/tickets/",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401