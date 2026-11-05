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
| 12 | Completed: tenant-admin summaries, pagination, Prometheus text, operator counters, privacy policy |
| 13 | Partial: sanitized spans and durable propagation verified; Docker permission blocks collector smoke |
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

## Day 12 — completed, 2026-11-05

- `app/api/monitoring.py`, `app/monitoring/queue_summary.py`: tenant-admin
  summaries, paginated jobs and Prometheus-compatible text. Separate optional
  operator token protects process-wide enqueue counters at `/metrics`.
- Aggregates include queue status/age, expired leases, retry count, completion
  throughput, processing duration, claim verdicts and existing persisted RAG
  metrics. Payloads excluded; scopes applied before aggregation.
- `docs/EVALUATION_DATA_POLICY.md` documents access, definitions, retention
  recommendation and why automatic destructive cleanup remains disabled.
- Targeted: `pytest tests/test_monitoring.py -q -p no:cacheprovider --tb=short`:
  **10 passed in 2.07s**. Regression baseline command: **116 passed in 11.24s**,
  including migrations. Providers mocked; no new dependency or migration.
- Limitations: process counters reset; no deployed scraper/UI. Historical RAG
  metric aggregates may be empty because live metric persistence is not wired.
  Suggested retention is policy documentation, not automated deletion.
- Next: trace correlation across the durable worker boundary (Day 13).

## Day 13 — partial; Docker runtime verification blocked, 2026-11-05

- Explicit tracing in `app/monitoring/tracing.py`: manual FastAPI ASGI spans,
  sanitized retrieval/reranking/generation/DB/worker spans. Exception text and
  stack events disabled. Attributes allowlisted; only traceparent propagated.
- Migration `1a13a0000001` adds nullable safe trace context and unique optional
  request ID to evaluation jobs. Existing jobs remain compatible. New request
  duplicates cannot create a second persisted job with the same request ID;
  no cross-HTTP-request deduplication guarantee is claimed.
- Worker restores context after claiming; queue wait/attempt/job metadata
  appears under the original request trace. Tests exercise the real evaluator
  parsing path with mocked provider responses.
- Added SDK and HTTP exporter 1.45.1 to existing UTF-16 requirements. Existing
  API version preserved; resolver added dependencies without replacing existing
  packages. `pip check`: no broken requirements.
- Added `docker-compose.tracing.yml` and `ops/otel-collector.yaml`; explicit
  opt-in settings; loopback host ports; no collector dependency for startup.
- `pytest tests/test_evaluation_submission.py tests/test_migrations.py -q -p no:cacheprovider --tb=short`:
  **29 passed in 2.57s**. `pytest tests/test_tracing.py tests/test_migrations.py -q -p no:cacheprovider --tb=short`:
  **9 passed in 0.72s**. Full regression: **124 passed in 11.67s**; no paid calls.
- Image manifest inspection verified linux/arm64 variants of
  `otel/opentelemetry-collector:0.147.0` and `jaegertracing/jaeger:2.5.0`.
- Compose config validation exited successfully. Attempted isolated startup:
  `docker compose -p copilot-tracing-check -f docker-compose.yml -f docker-compose.tracing.yml up -d --no-deps jaeger otel-collector`.
  Failed with Docker socket permission denied, before starting services.
- Verified request→durable queue→worker trace via in-memory exporter. No claim
  of collector/Jaeger runtime verification, deployment, or production migration.
- Next: restore Docker access (owner decision), run isolated collector smoke,
  verify a synthetic trace in Jaeger, stop only test services, then complete
  Day 13 and continue Day 14. Do not change socket permissions/group grants
  without explicit authorization. Days 14–30 remain unimplemented.
