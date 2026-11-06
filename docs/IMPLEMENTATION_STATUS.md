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
| 13 | Completed: trace propagation, privacy tests, real ARM64 collector/Jaeger smoke |
| 14 | Completed: authenticated bounded read-only LangGraph reusing RAG |
| 15 | Completed: typed read-only record tools, server authorization and bounded queries |
| 16 | Completed: measured PostgreSQL scaling ADR, concurrency, renewal and graceful shutdown |
| 17 | Completed: owner/tenant-scoped conversations and durable fenced graph checkpoints |
| 18 | Completed: durable human-approved ticket status changes with fenced execution |
| 19 | Completed assessment: no demonstrated policy gain; simpler production routing retained |
| 20 | Partial: tenant-bound read-only Slack adapter tested offline; live sandbox credentials pending |
| 21 | Completed: typed React shell, memory-only JWT login, proxy and interaction tests |
| 22 | Completed: conversations, composer, mode distinction, safe steps and source previews |
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

## Day 13 runtime completion — 2026-11-05

Docker membership was restored by the owner; this session still had stale
supplementary groups. `sg docker` used the existing membership without modifying
socket/account permissions. Docker Server 28.3.3 responded. Started only the
collector/Jaeger services in `copilot-tracing-check`, emitted one content-free
`smoke.synthetic` span with SDK force-flush, and fetched that exact trace from
Jaeger HTTP API. Result: force_flush True, one trace with smoke.synthetic.
Stopped only these test services afterward. No API/database service was started
or changed. This completes the pending runtime check; Day 14 is next.

## Day 14 — completed, 2026-11-05

`app/services/agent_service.py` / `app/api/agents.py`: typed acyclic LangGraph,
server-only frozen identity, auth recheck at each node, write refusal, existing
RAG reuse, safe steps, recursion limit and cooperative deadline. Provider HTTP
timeout 30s / zero retries; local model loads cannot be forcibly interrupted.
LangSmith capture disabled explicitly. Added langgraph1.2.20/core1.7.6 and
updated certifi to the required2026.10.23 pin. No schema changes.
Targeted:10passed in2.18s; full regression command:134passed in13.18s; pip check
passed. Models mocked. No push. Next: Day15 tenant-authorized typed tools.

## Day 15 — completed, 2026-11-05

Added tool_service.py, tool API/catalog and deterministic record-read graph
routing. Four read tools; no write capability. Strict argument models, tenant
filters, role/user recheck, independent transaction, output caps, SQL timeout
and sanitized errors/audit logs. No migration/dependency. Targeted command
`pytest tests/test_tools.py tests/test_agents.py -q -p no:cacheprovider --tb=short`:
20passed in4.41s. Full suite:144passed in15.88s. Initial Mock context-manager
test error fixed with MagicMock. Paid calls mocked, no external action/push.
Next: Day16 measured queue scalability decision and worker recovery improvements.

## Day16 — completed, 2026-11-05

Retained PostgreSQL after the40-job/1and4worker synthetic measurements in ADR001.
Added configurable1–8consumers, separate lease-renewal sessions, stale/expired
write fencing, poison-job classification and graceful signal drain. No new
dependency/migration. Targeted34passed in5.01s; full baseline regression
command:150passed in18.76s. Models mocked. Real production contention/throughput
unmeasured; no exactly-once inference claim. Next: Day17 durable conversations.

## Day17 — completed, 2026-11-05

Added conversation API/lifecycle and PostgreSQL BaseCheckpointSaver via existing
SQLAlchemy; four additive tables in migration1a17a0000001. Owner+tenant+active
user/run-token checks, short locks, explicit interrupted-run resume, bounded
untrusted history, logical expiry and idle-owner delete cascade. No dependency.
Initial checkpoint ordering defect fixed with separate pending-write storage;
delete conflict locks moved to an independent transaction. Stopped overlapping
test processes and reran serially. Reset only approved disposable migration DB
after prototype schema drift. Targeted7passed in2.74s; full regression156passed in26.31s, including migrations.
No development migration or paid model call. Next: Day18 human approvals.

## Day18 — completed, 2026-11-05

Approval models/service/router and migration1a18a0000001; graph persists proposals
only. Immutable API arguments/digest,15minute expiry, tenant/requester-scoped
idempotency, admin approve/reject then separate execution. Revalidate executor,
approver, expected ticket state and payload. Atomic local mutation/status/event
and row locks prevent double execution. No external write or native LangGraph
interrupt claim. Existing manual ticket CRUD retained. Targeted20passed in7.57s;
additional approval suite11passed in4.56s. Full regression167passed in33.32s, including migration alignment.
No new dependency/development migration/paid request. Next: Day19 coordination
assessment; adopt only if same-workload measurements justify complexity.

## Day19 — assessment completed, 2026-11-05

Offline typed one-node/three-role candidates over the same production authorized
read-tool service.50/50policy cases passed for each; single-node p50/p95
3.406/9.310ms, three-role3.742/7.213ms. No model calls or claimed live reasoning
gain. Candidate remains offline because no correctness improvement was shown;
ADR002 documents retaining simpler production routing per roadmap condition.
Targeted2passed in1.00s; full regression169passed in34.89s. No dependency,
schema change or remote action. Next: Day20 read-only sandbox connector.
Credential-presence checks found no generic Slack/Jira sandbox token; live
verification will require owner-provided sandbox access. Values were not printed.

## Day20 — offline implementation verified; live credentials pending

connector_service.py provides a provider-neutral read protocol and tenant-bound
Slack history adapter; connectors.py and explicit agent read routing reuse auth.
Fixed HTTPS host, per-tenant channel allowlist/token, bounded response/pagination,
no redirects/proxy inheritance, timeout/rate guard and bounded read-only retry.
No writes/webhooks or secret persistence in DB. Local environment secrets are
not a production encrypted vault. Official Slack method/rate docs checked.
18targeted tests passed in0.87s; full regression187passed in35.37s. No dependency
or migration. No live network request/paid call. Generic Slack/Jira sandbox
credentials were absent; tenant sandbox mapping is default-empty. Live verification
requires owner configuration and remains explicitly pending. Continue independent
frontend work without changing these claims or enabling a connector automatically.

## Day21 — completed locally, 2026-11-05

Added frontend/React19+TypeScript5.9+Vite7, React Router, typed client, protected
shell, responsive accessible login and memory-only JWT auth. Additive/auth/me
uses existing active-user dependency. No CORS widening/cookies/browser storage.
Optional Docker dev override and local setup docs; no hosting or dev-container
runtime claim. Node22.23.4/npm10.9.9 verified. npm install added166packages.
`npm test -- --reporter=dot`:4passed. `npm run build`:TypeScript+Vite passed.
Backend identity target1passed in0.33s; full188passed in35.42s including migrations.
No backend dependency/migration/paid calls. Sites local-only skill workflow used.
Next: Day22 conversations, grounded answers and citations. Day20 live Slack
verification remains pending at the owner's explicit direction.

## Day22 — completed locally, 2026-11-05

Conversation/knowledge UI with typed results, citations/authorized source preview,
abstention/errors, explicit resume and honest stop-waiting semantics. New preview
GET checks both tenant owners and caps returned content. No streaming/auto retry.
8frontend tests and build passed; source target1passed in0.38s; full backend
189passed in36.88s. No dependency/migration. Paid APIs mocked. Exact frontend
commands: npm --prefix frontend test -- --reporter=dot; npm --prefix frontend run build.
Next: Day23 admin/quality views backed by tenant-authorized APIs.
