def test_protected_endpoint_requires_login(client):
    response = client.get("/tickets/")
    assert response.status_code == 401


def test_invalid_login(client):
    response = client.post(
        "/auth/login",
        data={
            "username": "unknown@example.com",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401


def test_invalid_token(client):
    response = client.get(
        "/tickets/",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401