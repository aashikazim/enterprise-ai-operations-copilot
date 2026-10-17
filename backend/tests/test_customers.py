def test_get_customers(client, test_customer, admin_headers):
    response = client.get(
        "/customers/",
        headers=admin_headers,
    )

    assert response.status_code == 200

    customers = response.json()

    assert len(customers) == 1
    assert customers[0]["id"] == test_customer.id
    assert customers[0]["name"] == "Acme Corporation"


def test_get_customer_by_id(client, test_customer, admin_headers):
    response = client.get(
        f"/customers/{test_customer.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["email"] == "acme@example.com"


def test_get_customer_without_auth(client, test_customer):
    response = client.get(
        f"/customers/{test_customer.id}"
    )

    assert response.status_code == 401


def test_create_customer_disabled(client, admin_headers):
    response = client.post(
        "/customers/",
        json={
            "name": "New Company",
            "email": "newcompany@example.com",
        },
        headers=admin_headers,
    )

    assert response.status_code == 403