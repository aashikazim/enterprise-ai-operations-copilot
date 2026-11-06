# ADR002 — retain the simpler routed agent

Date:2026-11-05. Decision:do not enable a multi-agent production path yet.

A bounded typed LangGraph candidate separates support_triage,
knowledge_research and operations_planning. The same policy function runs in
one node for comparison. Both use the production authorized read-tool service,
the same authenticated context and identical five-case synthetic dataset,
repeated10times:own ticket, foreign ticket, missing ticket, malformed ID and
injection attempt. Candidates never execute writes. Failure stops safely.
This harness assesses policy behavior, not live LLM reasoning or the exact
end-to-end latency of the public agent API.

Command from backend:
`pytest tests/test_coordination_assessment.py -q -s -p no:cacheprovider --tb=short`.

|Shape|Policy cases passed|p50 ms|p95 ms|Model calls|
|---|---:|---:|---:|---:|
|One node|50/50|3.406|9.310|0|
|Three role nodes|50/50|3.742|7.213|0|

2tests passed in1.00s. No policy-correctness gain; latency differences are
single-run noise, not a claimed improvement. Model tokens/cost/factual quality
are unmeasured because no model calls occurred. Real model failures and
coordination quality need a separately authorized representative evaluation.
The current production graph already composes RAG, typed tools and durable
approvals with fewer handoffs. Keep it until a concrete workflow demonstrates
benefit. Candidate remains an offline assessment only; no extra deployment,
recursion or unapproved tool capabilities are introduced.
