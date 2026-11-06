from unittest.mock import Mock

import pytest

from app.services.agent_service import run_agent, AgentDeadlineExceeded
from app.services.rag_service import build_rag_result


def test_agent_reuses_rag_with_server_tenant(client, user_headers, test_user, monkeypatch):
    result = build_rag_result("Synthetic answer", [])
    answer = Mock(return_value=result)
    monkeypatch.setattr("app.services.agent_service.answer_question", answer)
    response = client.post("/agents/run", headers=user_headers, json={"question": "What is MFA?"})
    assert response.status_code == 200
    value = response.json()
    assert value["mode"] == "read_only" and value["result"] == result
    assert [s["node"] for s in value["steps"]] == ["classify", "knowledge"]
    assert answer.call_args.kwargs["customer_id"] == test_user.customer_id
    assert "user_id" not in response.text and "customer_id" not in response.text


@pytest.mark.parametrize("question", ["Update ticket 1", "delete all documents", "approve this action"])
def test_write_requests_cannot_execute_tools(client, user_headers, monkeypatch, question):
    answer = Mock()
    monkeypatch.setattr("app.services.agent_service.answer_question", answer)
    response = client.post("/agents/run", headers=user_headers, json={"question": question})
    assert response.status_code == 200
    assert response.json()["intent"] == "unsupported_action"
    assert response.json()["result"]["abstained"]
    answer.assert_not_called()


@pytest.mark.parametrize("payload", [{"question": "x", "customer_id": 99}, {"question": "   "}, {"question": "x", "top_k": 11}])
def test_invalid_agent_input(client, user_headers, payload):
    assert client.post("/agents/run", headers=user_headers, json=payload).status_code == 422


def test_agent_auth_and_failure_sanitization(client, user_headers, monkeypatch):
    assert client.post("/agents/run", json={"question": "x"}).status_code == 401
    monkeypatch.setattr("app.services.agent_service.answer_question", Mock(side_effect=RuntimeError("PRIVATE payload")))
    response = client.post("/agents/run", headers=user_headers, json={"question": "x"})
    assert response.status_code == 503 and "PRIVATE" not in response.text


def test_deadline_and_revoked_identity(db, test_user, monkeypatch):
    with pytest.raises(AgentDeadlineExceeded):
        run_agent(db, test_user, "x", timeout_seconds=0)
    test_user.is_active = False
    db.commit()
    with pytest.raises(PermissionError):
        run_agent(db, test_user, "x")


def test_no_langsmith_export_even_if_env_enabled(db, test_user, monkeypatch):
    from langsmith import get_tracing_context
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    observed = []
    def answer(**kwargs):
        observed.append(get_tracing_context()["enabled"])
        return build_rag_result("Synthetic", [])
    monkeypatch.setattr("app.services.agent_service.answer_question", answer)
    run_agent(db, test_user, "Synthetic question")
    assert observed == [False]
