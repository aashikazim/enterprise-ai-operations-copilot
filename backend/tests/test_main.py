
def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root(client):
    response = client.get("/")

    assert response.status_code == 200