def test_current_identity_requires_valid_jwt(client, user_headers, test_user):
    response = client.get("/auth/me")
    assert response.status_code == 401
    response = client.get("/auth/me", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["id"] == test_user.id
    assert response.json()["customer_id"] == test_user.customer_id
    assert "hashed_password" not in response.text
