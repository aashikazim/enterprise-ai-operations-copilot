"""Bounded read-only LangGraph workflow over the existing grounded RAG service."""
from dataclasses import dataclass
import re
from time import monotonic
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import StateGraph, START, END
from langsmith import tracing_context

from app.db.models import User
from app.monitoring.tracing import span
from app.services.rag_service import answer_question, build_rag_result, ABSTENTION_MESSAGE
from app.services.tool_service import execute_tool


@dataclass(frozen=True)
class AgentIdentity:
    user_id: int
    customer_id: int


class AgentState(TypedDict, total=False):
    question: str
    intent: str
    result: dict
    steps: list[dict]
    tool_name: str
    tool_arguments: dict
    tool_results: list[dict]


class AgentDeadlineExceeded(TimeoutError):
    pass


def run_agent(db, user, question, top_k=5, timeout_seconds=45):
    identity = AgentIdentity(user.id, user.customer_id)
    request_id = str(uuid4())
    deadline = monotonic() + timeout_seconds

    def authorized():
        if monotonic() >= deadline:
            raise AgentDeadlineExceeded("Agent deadline exceeded")
        # Recheck server identity at node boundaries. Model state contains no
        # identity/role fields and cannot select another tenant.
        active = db.get(User, identity.user_id, populate_existing=True)
        if not active or not active.is_active or active.customer_id != identity.customer_id:
            raise PermissionError("Agent identity is no longer authorized")

    def classify(state):
        authorized()
        with span("agent.classify", **{"request.id": request_id}):
            write = re.match(r"\s*(create|update|delete|close|reopen|assign|send|post|approve)\b", state["question"], re.I)
            question = state["question"].strip().lower()
            tool_name, arguments = None, {}
            if question in {"list tickets", "show tickets"}:
                tool_name = "tickets.list"
            elif question in {"list documents", "show documents"}:
                tool_name = "documents.list"
            elif question in {"show customer", "show my customer"}:
                tool_name = "customers.current"
            elif match := re.fullmatch(r"(?:show|get) ticket (\d+)", question):
                tool_name, arguments = "tickets.get", {"ticket_id": int(match.group(1))}
            if tool_name and not write:
                return {"intent": "records", "tool_name": tool_name, "tool_arguments": arguments,
                        "steps": [{"node": "classify", "status": "completed"}]}
            return {"intent": "unsupported_action" if write else "knowledge",
                    "steps": [{"node": "classify", "status": "completed"}]}

    def answer(state):
        authorized()
        with span("agent.knowledge", **{"request.id": request_id}):
            result = answer_question(db=db, question=state["question"], customer_id=identity.customer_id, top_k=top_k)
        authorized()
        return {"result": result, "steps": state["steps"] + [{"node": "knowledge", "status": "completed"}]}

    def refuse(state):
        authorized()
        return {"result": build_rag_result(ABSTENTION_MESSAGE, []),
                "steps": state["steps"] + [{"node": "write_not_enabled", "status": "blocked"}]}

    def records(state):
        authorized()
        output = execute_tool(db, user, state["tool_name"], state["tool_arguments"])
        authorized()
        return {"result": build_rag_result(f"Found {len(output['items'])} authorized records.", []),
                "tool_results": [output],
                "steps": state["steps"] + [{"node": state["tool_name"], "status": "completed"}]}

    graph = StateGraph(AgentState)
    graph.add_node("classify", classify)
    graph.add_node("answer", answer)
    graph.add_node("refuse", refuse)
    graph.add_node("records", records)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", lambda state: state["intent"],
                               {"knowledge": "answer", "unsupported_action": "refuse", "records": "records"})
    graph.add_edge("answer", END)
    graph.add_edge("refuse", END)
    graph.add_edge("records", END)
    # Disable external LangSmith capture even if a shell enables it. Our
    # OpenTelemetry spans contain safe metadata only, never graph payloads.
    with tracing_context(enabled=False), span("agent.run", **{"request.id": request_id}):
        value = graph.compile().invoke({"question": question}, {"recursion_limit": 6, "callbacks": []})
    return {"request_id": request_id, "mode": "read_only", "intent": value["intent"],
            "result": value["result"], "steps": value["steps"], "tool_results": value.get("tool_results", [])}
