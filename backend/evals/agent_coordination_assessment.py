"""Offline bounded policy harness: one node versus three specialist nodes.

This evaluates deterministic tool-policy correctness/latency, not live model
reasoning quality. The candidate is not exposed as a production agent API.
"""
import re
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langsmith import tracing_context
from pydantic import ValidationError

from app.services.tool_service import execute_tool, ToolNotFound, ToolUnavailable


class AssessmentState(TypedDict, total=False):
    question: str
    ticket_id: int | None
    records: list
    status: str
    result: dict


def build_assessment(db, user, coordinated=False):
    def triage(state):
        match = re.fullmatch(r"triage ticket ([1-9]\d{0,9})", state["question"])
        return {"ticket_id": int(match.group(1)) if match else None, "status": "valid" if match else "invalid"}

    def research(state):
        if state["status"] == "invalid":
            return {"records": []}
        try:
            result = execute_tool(db, user, "tickets.get", {"ticket_id": state["ticket_id"]})
            return {"records": result["items"], "status": "ok"}
        except (ToolNotFound, PermissionError):
            return {"records": [], "status": "denied"}
        except (ToolUnavailable, ValidationError):
            return {"records": [], "status": "unavailable"}

    def plan(state):
        return {"result": {"status": state["status"], "ticket_ids": [r["id"] for r in state["records"]],
                           "write_executed": False}}

    def single(state):
        state = {**state, **triage(state)}
        state.update(research(state))
        return plan(state)

    graph = StateGraph(AssessmentState)
    if coordinated:
        graph.add_node("support_triage", triage)
        graph.add_node("knowledge_research", research)
        graph.add_node("operations_planning", plan)
        graph.add_edge(START, "support_triage")
        graph.add_edge("support_triage", "knowledge_research")
        graph.add_edge("knowledge_research", "operations_planning")
        graph.add_edge("operations_planning", END)
    else:
        graph.add_node("single", single)
        graph.add_edge(START, "single")
        graph.add_edge("single", END)
    compiled = graph.compile()
    def invoke(question):
        with tracing_context(enabled=False):
            return compiled.invoke({"question": question}, {"recursion_limit": 6, "callbacks": []})["result"]
    return invoke
