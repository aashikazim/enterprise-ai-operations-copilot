from unittest.mock import Mock


def test_readiness_database_and_failure(client, monkeypatch):
    assert client.get('/ready').json() == {'status': 'ready'}
    monkeypatch.setattr('app.db.database.SessionLocal', Mock(side_effect=RuntimeError('PRIVATE DSN')))
    response = client.get('/ready')
    assert response.status_code == 503
    assert response.json() == {'status': 'unavailable'}
