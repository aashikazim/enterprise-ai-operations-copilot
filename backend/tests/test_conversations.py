from datetime import timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker

from app.db.conversation_models import Conversation, ConversationMessage, AgentCheckpoint, now
from app.db.models import Customer, User
from app.auth.security import create_access_token, hash_password
from app.services.conversation_service import TenantCheckpointSaver, history_context, ConversationBusy
from app.services.rag_service import build_rag_result


def create(client, headers):
    response = client.post("/conversations", headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def test_durable_roundtrip_and_bounded_history(client, db, user_headers, monkeypatch):
    identifier = create(client, user_headers)
    answer = Mock(return_value=build_rag_result("Synthetic answer", []))
    monkeypatch.setattr("app.services.agent_service.answer_question", answer)
    response = client.post(f"/conversations/{identifier}/messages", headers=user_headers,
                           json={"question": "First synthetic question"})
    assert response.status_code == 200
    assert db.scalar(select(func.count()).select_from(AgentCheckpoint)) > 0
    # Every invocation compiles a new graph and opens new saver sessions, so
    # this tests persistence rather than retaining a Python in-memory graph.
    response = client.post(f"/conversations/{identifier}/messages", headers=user_headers,
                           json={"question": "Follow up"})
    assert response.status_code == 200
    assert "First synthetic question" in answer.call_args.kwargs["question"]
    detail = client.get(f"/conversations/{identifier}", headers=user_headers)
    assert len(detail.json()["messages"]) == 4
    assert len(client.get("/conversations", headers=user_headers).json()["items"]) == 1
    db.add(ConversationMessage(conversation_id=identifier, role="user", content="x" * 10000))
    db.commit()
    assert len(history_context(db, identifier).encode()) <= 4000


def test_interrupted_run_resumes_checkpoint(client, db, user_headers, monkeypatch):
    identifier = create(client, user_headers)
    answer = Mock(side_effect=RuntimeError("PRIVATE provider failure"))
    monkeypatch.setattr("app.services.agent_service.answer_question", answer)
    response = client.post(f"/conversations/{identifier}/messages", headers=user_headers, json={"question": "Synthetic"})
    assert response.status_code == 503 and "PRIVATE" not in response.text
    assert db.get(Conversation, identifier).status == "interrupted"
    monkeypatch.setattr("app.services.agent_service.answer_question", lambda **kwargs: build_rag_result("Recovered", []))
    response = client.post(f"/conversations/{identifier}/resume", headers=user_headers)
    assert response.status_code == 200 and response.json()["result"]["answer"] == "Recovered"
    assert len(client.get(f"/conversations/{identifier}", headers=user_headers).json()["messages"]) == 2


def test_same_and_foreign_tenant_users_cannot_access(client, db, user_headers, test_user):
    identifier = create(client, user_headers)
    other = Customer(name="Foreign", email="memory-foreign@example.com")
    db.add(other)
    db.flush()
    users = [User(email=f"memory-{n}@example.com", hashed_password=hash_password("SyntheticPassword!"),
                  customer_id=customer_id, role="admin") for n, customer_id in enumerate([test_user.customer_id, other.id])]
    db.add_all(users)
    db.commit()
    for user in users:
        headers = {"Authorization": "Bearer " + create_access_token(user.id)}
        assert client.get(f"/conversations/{identifier}", headers=headers).status_code == 404
        assert client.post(f"/conversations/{identifier}/messages", headers=headers, json={"question": "x"}).status_code == 404
        assert client.delete(f"/conversations/{identifier}", headers=headers).status_code == 404
        assert client.get("/conversations", headers=headers).json()["items"] == []


def test_expiry_busy_and_delete_cascade(client, db, user_headers, monkeypatch):
    identifier = create(client, user_headers)
    monkeypatch.setattr("app.services.agent_service.answer_question", lambda **kwargs: build_rag_result("Synthetic", []))
    response = client.post(f"/conversations/{identifier}/messages", headers=user_headers, json={"question": "x"})
    assert response.status_code == 200
    value = db.get(Conversation, identifier)
    value.lease_expires_at = now() + timedelta(seconds=120)
    db.commit()
    assert client.delete(f"/conversations/{identifier}", headers=user_headers).status_code == 409
    assert client.post(f"/conversations/{identifier}/messages", headers=user_headers, json={"question": "x"}).status_code == 409
    value.lease_expires_at = None
    db.commit()
    assert client.delete(f"/conversations/{identifier}", headers=user_headers).status_code == 204
    assert db.scalar(select(func.count()).select_from(AgentCheckpoint)) == 0
    assert db.scalar(select(func.count()).select_from(ConversationMessage)) == 0
    identifier = create(client, user_headers)
    db.get(Conversation, identifier).expires_at = now() - timedelta(seconds=1)
    db.commit()
    assert client.get(f"/conversations/{identifier}", headers=user_headers).status_code == 404


def test_checkpoint_scope_and_fenced_run(db, test_user):
    conversation = Conversation(customer_id=test_user.customer_id, user_id=test_user.id,
                                run_token="current", lease_expires_at=now() + timedelta(seconds=120))
    db.add(conversation)
    db.commit()
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    saver = TenantCheckpointSaver(factory, conversation.id, test_user.id, test_user.customer_id, "current")
    with pytest.raises(PermissionError):
        saver.get_tuple({"configurable": {"thread_id": "foreign"}})
    stale = TenantCheckpointSaver(factory, conversation.id, test_user.id, test_user.customer_id, "stale")
    with pytest.raises(ConversationBusy):
        stale.get_tuple({"configurable": {"thread_id": conversation.id}})


def test_conversation_auth_validation(client, user_headers):
    assert client.post("/conversations").status_code == 401
    assert client.post("/conversations/bad/messages", headers=user_headers,
                       json={"question": "x", "customer_id": 3}).status_code == 422
