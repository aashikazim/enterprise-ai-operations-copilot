import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from pydantic import SecretStr

from app.services import connector_service as connectors


@pytest.fixture
def configured(monkeypatch):
    settings = SimpleNamespace(slack_tenant_credentials=SecretStr(json.dumps({
        "1": {"bot_token": "xoxb-synthetic-secret", "channel_ids": ["C12345678"]},
        "2": {"bot_token": "xoxb-other-synthetic-secret", "channel_ids": ["C87654321"]},
    })))
    monkeypatch.setattr(connectors, "get_settings", lambda: settings)
    monkeypatch.setattr(connectors, "rate_limiter", connectors.ReadRateLimiter())
    return settings


def test_fixed_host_token_scope_and_pagination(configured):
    seen = []
    def handle(request):
        seen.append(request)
        assert request.url.scheme == "https" and request.url.host == "slack.com"
        assert request.headers["Authorization"] == "Bearer xoxb-synthetic-secret"
        assert request.url.params["channel"] == "C12345678"
        assert "xoxb" not in str(request.url)
        return httpx.Response(200, json={"ok": True, "messages": [{"text": "Synthetic", "ts": "1.0", "user": "not-returned"}],
                                          "response_metadata": {"next_cursor": "next="}})
    value = connectors.SlackReadConnector(1, transport=httpx.MockTransport(handle)).read_page("C12345678", 1, "page=")
    assert value == {"provider": "slack", "items": [{"text": "Synthetic", "timestamp": "1.0", "truncated": False}], "next_cursor": "next="}
    assert len(seen) == 1


def test_channel_tenant_denial_before_network(configured):
    handler = Mock()
    adapter = connectors.SlackReadConnector(1, transport=httpx.MockTransport(handler))
    with pytest.raises(PermissionError): adapter.read_page("C87654321")
    handler.assert_not_called()


@pytest.mark.parametrize("payload", ["{}", "not json", '{"1":{"bot_token":"bad","channel_ids":[]}}'])
def test_offline_and_bad_config(configured, payload):
    configured.slack_tenant_credentials = SecretStr(payload)
    with pytest.raises(connectors.ConnectorUnavailable): connectors.SlackReadConnector(1)


@pytest.mark.parametrize("limit,cursor", [(16, ""), (True, ""), (1, "https://evil.example")])
def test_reject_invalid_pagination(configured, limit, cursor):
    adapter = connectors.SlackReadConnector(1)
    with pytest.raises(ValueError): adapter.read_page("C12345678", limit, cursor)


def test_bounded_rate_limit_retry(configured):
    calls, sleeps = [], []
    def handle(request):
        calls.append(request)
        if len(calls) == 1: return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json={"ok": True, "messages": []})
    adapter = connectors.SlackReadConnector(1, transport=httpx.MockTransport(handle), sleep=sleeps.append)
    assert adapter.read_page("C12345678")["items"] == []
    assert len(calls) == 2 and sleeps == [1]


def test_long_rate_limit_does_not_block_worker(configured):
    handler = Mock(return_value=httpx.Response(429, headers={"Retry-After": "60"}))
    adapter = connectors.SlackReadConnector(1, transport=httpx.MockTransport(handler), sleep=Mock())
    with pytest.raises(connectors.ConnectorRateLimited) as error: adapter.read_page("C12345678")
    assert error.value.retry_after == 60 and handler.call_count == 1
    adapter.sleep.assert_not_called()


def test_redirect_never_forwards_token(configured):
    handler = Mock(return_value=httpx.Response(302, headers={"Location": "https://evil.example"}))
    adapter = connectors.SlackReadConnector(1, transport=httpx.MockTransport(handler))
    with pytest.raises(connectors.ConnectorUnavailable): adapter.read_page("C12345678")
    assert handler.call_count == 1


@pytest.mark.parametrize("payload", [{"ok": False, "error": "PRIVATE PROVIDER ERROR"},
    {"ok": True, "messages": "invalid"}, {"ok": True, "messages": [{"text": "x"}]},
    {"ok": True, "messages": [], "response_metadata": {"next_cursor": "https://evil.example"}}])
def test_provider_schema_errors_sanitized(configured, payload):
    adapter = connectors.SlackReadConnector(1, transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)))
    with pytest.raises(connectors.ConnectorUnavailable) as error: adapter.read_page("C12345678")
    assert "PRIVATE" not in str(error.value)


def test_local_rate_limit(configured):
    adapter = connectors.SlackReadConnector(1, transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"ok": True, "messages": []})))
    adapter.read_page("C12345678")
    with pytest.raises(connectors.ConnectorRateLimited): adapter.read_page("C12345678")


def test_api_auth_offline_and_input(client, user_headers, monkeypatch):
    monkeypatch.setattr(connectors, "get_settings", lambda: SimpleNamespace(slack_tenant_credentials=SecretStr("{}")))
    response = client.get("/connectors/slack/history?channel_id=C12345678")
    assert response.status_code == 401
    response = client.get("/connectors/slack/history?channel_id=C12345678", headers=user_headers)
    assert response.status_code == 503 and "xoxb" not in response.text
    response = client.get("/connectors/slack/history?channel_id=https://evil.example", headers=user_headers)
    assert response.status_code == 422


def test_graph_connector_identity_is_server_bound(client, user_headers, test_user, monkeypatch):
    adapter = Mock()
    adapter.read_page.return_value = {"provider": "slack", "items": [], "next_cursor": ""}
    constructor = Mock(return_value=adapter)
    monkeypatch.setattr("app.services.agent_service.SlackReadConnector", constructor)
    response = client.post("/agents/run", headers=user_headers, json={"question": "read slack channel C12345678"})
    assert response.status_code == 200 and response.json()["intent"] == "connector_read"
    constructor.assert_called_once_with(test_user.customer_id)
    adapter.read_page.assert_called_once_with("C12345678")


def test_connector_timeout_is_bounded_and_sanitized(configured):
    handler = Mock(side_effect=httpx.ReadTimeout('PRIVATE transport failure'))
    adapter = connectors.SlackReadConnector(1, transport=httpx.MockTransport(handler), sleep=Mock())
    with pytest.raises(connectors.ConnectorUnavailable) as error:
        adapter.read_page('C12345678')
    assert 'PRIVATE' not in str(error.value)
    assert handler.call_count <= 2
