# Day 11 — durable sampled faithfulness evaluation

Date: 2026-11-05. Status: completed with mocked providers and real PostgreSQL.

## Architecture and decisions

Reuse existing RAG and PostgreSQL queue. A request gets an opaque UUID, runs
existing retrieval/generation, builds its unchanged response, then optionally
submits an evaluation. Default-off flags avoid unexpected data retention/cost.
Sampling is stable for a request ID, uniformly bucketed using SHA-256, with
explicit 0/1 boundaries. There is no high-risk classifier or automatic trust
decision based on a score.

Returned source metadata has no full text. The service carries original
ordered retrieval snapshots internally and rechecks chunk/document ownership,
IDs, content and titles using a separate DB session. Evidence is rejected as a
unit if it changed; filtering individual rows would renumber citations.

Existing enqueue commits its own transaction. A separate session prevents it
from committing request work. On failure the context manager rolls back only
evaluation work, the answer remains usable, and a fixed safe outcome is logged.
The evaluator still runs only in the worker. Short claim/write transactions
surround model execution; stale attempt numbers cannot replace newer results.

## Debugging and verification

The sandbox blocks local PostgreSQL networking. Baseline rerun with approved
host access: 78 passed in 7.38s. Initial transaction-isolation tests failed
because accessing an expired customer fixture after adding pending state
triggered SQLAlchemy autoflush in the test itself. Resolve its ID first.

Targeted corrected run: 30 passed in 1.60s. Final regression:

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/ -q -p no:cacheprovider --tb=short
```

106 passed in 9.14s, including the full migration chain, source isolation,
API response contract, independent commit/rollback, worker completion, retries,
expired/exhausted leases and stale completion fencing. Paid APIs/embeddings
mocked. No new migrations/dependencies. No development database writes.

Timing probe:
`pytest tests/test_evaluation_submission.py::test_local_enqueue_overhead -q -s -p no:cacheprovider`.
It measures 20 local DB enqueues using two synthetic evidence chunks, not model
latency, end-to-end load, concurrent throughput or a production guarantee.
Observed on this host: p50 6.915 ms, nearest-rank p95 8.339 ms; probe passed
in 0.37s. Dependency consistency check reported no broken requirements.

## FDE interview questions

1. **Why not evaluate inline?** It adds another model call, cost and failure
   dependency to every answer. A durable worker isolates those concerns.
2. **Why another session?** Existing enqueue commits; sharing the request
   session would commit unrelated state and couple rollback behavior.
3. **Why preserve evidence ordering?** Source numbers refer to positions in
   the generated context, not document IDs. Reordering breaks attribution.
4. **What does a valid citation prove?** Only that the referenced number exists.
   Claim support is a separate structured evaluator judgment with limitations.
5. **What delivery semantics apply?** At-least-once inference after lease expiry;
   attempt fencing prevents stale result writes, not duplicated provider cost.
6. **What happens on DB failure?** Return the answer, emit safe failure telemetry,
   and do not acknowledge a successfully queued evaluation.
7. **What remains risky?** Retained evidence/privacy, model errors, queue delay,
   synchronous enqueue waits and sampling blind spots. Disable for unapproved
   datasets; use human review for high-stakes claims.
