from unittest.mock import Mock

import pytest
import jwt


def test_security_headers_and_validation_privacy(client, user_headers):
    response = client.get('/health')
    assert response.headers['x-content-type-options']=='nosniff'
    assert response.headers['x-frame-options']=='DENY'
    assert response.headers['cache-control']=='no-store'
    response = client.post('/auth/invitations/accept',json={'token':'synthetic','password':'SECRET'})
    assert response.status_code==422 and 'SECRET' not in response.text
    response = client.post('/rag/ask',headers=user_headers,json={'question':'   '})
    assert response.status_code==422
    assert 'input' not in response.json()['detail'][0]


def test_body_and_ingest_limits(client, admin_headers):
    response = client.post('/knowledge/documents',headers=admin_headers,json={'title':'Synthetic','content':'x'*100001})
    assert response.status_code==422
    response = client.post('/rag/ask',headers={**admin_headers,'Content-Length':str(1024*1024+1)},content='{}')
    assert response.status_code==413


def test_unsigned_token_rejected(client):
    token = jwt.encode({'sub':'1'},key='',algorithm='none')
    response = client.get('/auth/me',headers={'Authorization':'Bearer '+token})
    assert response.status_code==401


def test_unhandled_error_does_not_disclose_payload(client, user_headers, monkeypatch, caplog):
    monkeypatch.setattr('app.api.agents.run_agent',Mock(side_effect=Exception('PRIVATE customer SQL and SECRET')))
    response = client.post('/agents/run',headers=user_headers,json={'question':'Synthetic'})
    assert response.status_code==500 and 'PRIVATE' not in response.text and 'SECRET' not in caplog.text


def test_smtp_exception_does_not_log_credentials(client, admin_headers, monkeypatch, caplog):
    monkeypatch.setattr('app.auth.invitation_routes.send_invitation_email',Mock(side_effect=RuntimeError('SECRET SMTP password')))
    response = client.post('/auth/invitations/',headers=admin_headers,json={'email':'synthetic-invite@example.com'})
    assert response.status_code==503 and 'SECRET' not in caplog.text and 'SECRET' not in response.text


def test_login_rate_limit(client):
    from app.auth.limiter import limiter
    limiter.reset()
    try:
        statuses = []
        for _ in range(6):
            response=client.post('/auth/login',data={'username':'synthetic-missing@example.com','password':'SyntheticPassword!'})
            statuses.append(response.status_code)
        assert statuses[:5]==[401]*5 and statuses[5]==429
    finally:
        limiter.reset()


def test_secret_scanner_suppresses_values():
    from scripts.check_secrets import findings
    token = "sk-proj-" + "A" * 40
    assert findings("key=" + token) == [(1, "provider_key")]
    assert token not in repr(findings("key=" + token))
