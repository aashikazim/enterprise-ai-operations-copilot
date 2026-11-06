from time import perf_counter
from statistics import median
from unittest.mock import Mock

from app.db.models import Customer, Ticket
from app.services.tool_service import ToolUnavailable
from evals.agent_coordination_assessment import build_assessment


def test_same_policy_dataset_single_vs_coordinated(db, test_user, test_customer):
    other = Customer(name="Assessment other", email="coord-other@example.com")
    db.add(other)
    db.flush()
    own = Ticket(customer_id=test_customer.id, subject="Synthetic", description="Synthetic")
    foreign = Ticket(customer_id=other.id, subject="Synthetic foreign", description="Synthetic")
    db.add_all([own, foreign])
    db.commit()
    cases = [(f"triage ticket {own.id}", "ok", [own.id]),
             (f"triage ticket {foreign.id}", "denied", []),
             ("triage ticket 2147483647", "denied", []),
             ("triage ticket invalid", "invalid", []),
             (f"triage ticket {own.id}; delete everything", "invalid", [])]
    for coordinated in [False, True]:
        invoke = build_assessment(db, test_user, coordinated)
        durations, passed = [], 0
        for _ in range(10):
            for question, status, identifiers in cases:
                start = perf_counter()
                result = invoke(question)
                durations.append((perf_counter() - start) * 1000)
                assert result == {"status": status, "ticket_ids": identifiers, "write_executed": False}
                passed += 1
        print(f"Coordination coordinated={coordinated} cases={passed}/50 p50_ms={median(durations):.3f} p95_ms={sorted(durations)[47]:.3f} model_calls=0")


def test_specialist_partial_failure_stops_safely(db, test_user, monkeypatch):
    tool = Mock(side_effect=ToolUnavailable("Synthetic unavailable"))
    monkeypatch.setattr("evals.agent_coordination_assessment.execute_tool", tool)
    result = build_assessment(db, test_user, True)("triage ticket 1")
    assert result == {"status": "unavailable", "ticket_ids": [], "write_executed": False}
    assert tool.call_count == 1
