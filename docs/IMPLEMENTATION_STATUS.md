# Verified implementation status

Audit date: 2026-11-05. Branch: `main`. Starting commit: `e34d649`.
The starting working tree was clean. This document reports code and commands,
not assumed historical capabilities.

## Repository map and audit

| Component | Actual paths / verified behavior |
|---|---|
| API | `backend/app/main.py`; routers in `app/api/`; health is process liveness only |
| Identity | `app/auth/dependencies.py`, `security.py`, `routes.py`; verified JWT resolves active DB user; admin checks server-side |
| Registration | `app/auth/invitation_routes.py`; invite-only; public registration disabled |
| Entities | `app/db/models.py`; customers, users, documents, chunks, tickets, invitations |
| Retrieval | `app/services/retrieval_service.py`, `bm25_retrieval_service.py`, `hybrid_retrieval_service.py`, `reranking_service.py`; tenant filters on both document and chunk; BM25 active since Day 11A |
| RAG | `app/api/rag.py`, `app/services/rag_service.py`, `llm_service.py`; source numbers preserve ordered evidence; syntax validation does not prove claim support |
| Evaluation | `app/services/faithfulness_service.py`; structured claims, sequential source IDs, separate evaluator API call |
| Queue | `app/jobs/evaluation_queue.py`, `retry_policy.py`, `app/db/evaluation_job_model.py`; PostgreSQL row locks, attempt fencing, leases, bounded backoff |
| Worker | `app/workers/evaluation_worker.py`; standalone polling loop; no lease renewal at audit |
| Metrics | `app/monitoring/`, `app/db/rag_metric_model.py`; persistence helper exists; live request metrics disconnected at audit |
| Migrations | `backend/migrations/versions/`; head `1a11a0000001` repairs metrics and GIN index; vector extension must precede historical migrations |
| Tests | `backend/tests/`; two allowlisted disposable DBs guarded in `conftest.py` and `scripts/prepare_test_database.py` |
| Deployment | root `docker-compose.yml`: API + PostgreSQL; `backend/Dockerfile`; no worker service, frontend, CI, lint/type configuration or env example at audit |

Dependencies are pinned in UTF-16 `backend/requirements.txt`; psycopg 3,
FastAPI/SQLAlchemy/Alembic, Sentence Transformers, rank-bm25, OpenAI.
OpenTelemetry API alone is installed; no tracing SDK/exporter configuration.
Historical `docs/architecture.md` depicts React/LangGraph that do not yet exist.
The synchronized component map is now `docs/ARCHITECTURE.md`.

## Baseline evidence

From `backend/`:
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/ -q -p no:cacheprovider --tb=no`

- Network-restricted sandbox: 41 passed, 1 failed, 36 setup errors (database connections).
- Outside that sandbox: **78 passed in 7.38s**. No paid APIs called.
- Existing test fixtures reset only approved disposable DBs. No development
  database migrations or production changes are authorized by test execution.

## Roadmap status

| Day | Status |
|---|---|
| 11 | Completed: opt-in sampled durable evaluation; independent transaction; tenant snapshot checks; worker tests |
| 12 | Planned: tenant monitoring and queue observability |
| 13 | Planned: sanitized tracing |
| 14 | Planned: bounded LangGraph workflow |
| 15 | Planned: typed tenant-authorized tools |
| 16 | Planned: queue benchmark and scaling ADR |
| 17 | Planned: durable conversations/checkpoints |
| 18 | Planned: approval state machine |
| 19 | Planned: bounded coordination assessment |
| 20 | Planned: sandbox connector; live verification requires credentials |
| 21 | Planned: React/TypeScript shell |
| 22 | Planned: chat/citations |
| 23 | Planned: admin dashboard |
| 24 | Planned: execution/approval UI |
| 25 | Planned: security review and negative tests |
| 26 | Planned: measured optimization |
| 27 | Planned: reproducible full-stack containers |
| 28 | Planned: AWS runbook; cloud spending/deployment requires approval |
| 29 | Planned: E2E/fault verification |
| 30 | Planned: demo and portfolio handoff |

## Boundaries and known limitations

No claim of production readiness or provider invoice accuracy. No live LLM
or external connector verification is required for offline test gates.
Existing model prices in code are estimates, not newly verified current prices.
BM25 rebuilds in memory per request; no ANN index, lease heartbeat, or durable
conversation exists at audit. Evaluation payload retention/access policy is
required before real sensitive customer data. Cloud actions and credential
provisioning remain explicit owner decisions.

## Day 11 — completed, 2026-11-05

- Added validated default-off `RAG_EVAL_ENABLED` and sample rate; deterministic
  UUID hashing. No HTTP request/response schema changes or new dependencies.
- `app/services/evaluation_submission.py` rechecks both tenant owners and exact
  ordered content/title/IDs in an independent session before durable enqueue.
  Request sessions are never committed/rolled back by enqueue.
- `app/monitoring/evaluation_metrics.py` records safe fixed outcomes and
  aggregate enqueue durations. No payloads or SQL/provider exception strings.
- Worker `process_next_job` permits real DB-to-worker tests with a mocked
  evaluator and no DB transaction held during model execution. Attempt fencing,
  backoff and expired/exhausted lease behavior verified.
- Added placeholder `backend/.env.example`; Compose forwards opt-in settings.
- Targeted tests initially had two fixture-autoflush assertion failures; fixed
  by resolving expired fixture IDs before adding unrelated pending records.
- Regression command: baseline command above with `--tb=short` instead of
  `--tb=no`: **106 passed in 9.14s**. Full migration-chain test included.
- No paid model invocation, development schema change, or remote push.
- Synthetic enqueue timing: 20 two-chunk jobs, p50 6.915 ms / p95 8.339 ms;
  a local DB microbenchmark, not end-to-end or concurrent performance evidence.
- Limitations: no risk classifier; no inline faithfulness gate; DB enqueue is
  synchronous and can add connection/statement wait. No job ID in unchanged
  RAG response. Cross-request idempotency is not claimed. Sampling disabled
  means zero evaluation payload writes. Next: tenant-safe monitoring (Day 12).
