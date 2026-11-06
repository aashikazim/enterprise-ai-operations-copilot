# Day 14 — bounded read-only LangGraph

Status: completed with mocked models and real PostgreSQL. Date: 2026-11-05.

## Architecture and decisions

Add `app/services/agent_service.py` and `app/api/agents.py`; preserve RAG.
Typed state contains a question, intent, result and safe steps. Frozen identity
comes from the verified user, never request/LLM fields. Classify routes to the
existing RAG function or refuses writes. Fixed acyclic edges, recursion limit 6
and a cooperative 45-second deadline prevent recursive tool loops. A call
already in a local embedding load cannot be hard-killed; document that limit.
Model client timeout is 30s with automatic retries disabled.

LangGraph 1.2.20 and langchain-core 1.7.6 are pinned. Resolver required certifi
2026.10.23; its existing pin was updated. No database migration. External
LangSmith tracing is explicitly disabled around graph execution to prevent
shell settings exporting customer payloads. Sanitized OTel spans remain.
Official [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
documents typed state, fixed/conditional edges and recursion limits.

## Verification

`pytest tests/test_agents.py -q -p no:cacheprovider --tb=short`: 10 passed in
2.18s. Covers actual graph routing, auth, unchecked tenant rejection, writes
refused, deadline, identity revocation, sanitized errors and tracing disabled.
Full regression and dependency results are recorded in IMPLEMENTATION_STATUS.
Paid APIs mocked; no live agent quality benchmark is claimed.

## FDE interview questions

1. **Why keep RAG separate?** It is a stable tested API and reusable capability;
   graph orchestration should not duplicate retrieval/security logic.
2. **Why not ask the LLM for tenant IDs?** Model output is untrusted. Identity
   must originate in authentication and remain outside writable model state.
3. **What bounds execution?** Fixed graph, recursion limit, per-call provider
   timeout and cooperative deadline. These are not OS-level process cancellation.
4. **Why refuse writes?** No approval state machine exists yet; retrieval text
   and user language cannot authorize enterprise mutations by themselves.
5. **Why disable graph-payload tracing?** Framework callbacks may capture entire
   state. Explicit safe OTel metadata is sufficient for this milestone.
6. **What remains?** Typed tools, durable checkpointing, approvals and measured
   quality; a deterministic mocked path does not establish live model accuracy.
