# Verified development changelog

Days1–10 are historical capability groups verified against the starting code;
this is not a claim to have recreated their original daily commit chronology.

| Day | Delivered or verified result |
|---|---|
| 1–4 | Existing FastAPI/entities, PostgreSQL/Alembic, JWT/RBAC, tenant filtering and invite-only onboarding |
| 5 | Existing384-dimensional embeddings/chunks and pgvector retrieval |
| 6 | Existing RAG generation/source contract and retrieval metric utilities |
| 7 | Hybrid/RRF/reranker existed; true BM25 connected during11A |
| 8 | Existing numbered-citation validation and abstention |
| 9 | Existing structured claim evaluator and metric persistence helpers; live aggregate wiring repaired on29 |
| 10 | Existing durable PostgreSQL job queue/worker/API; automatic RAG enqueue added on11 |
| 11A | Additive missing metric/FTS repair, genuine BM25 integration, isolated DB/migration tests |
| 11 | Sampled async RAG evaluation, independent transactions and tenant evidence checks |
| 12 | Tenant quality/queue APIs, Prometheus aggregates and privacy policy |
| 13 | Sanitized tracing and cross-job context; native collector/Jaeger smoke |
| 14 | Bounded authenticated LangGraph reusing RAG |
| 15 | Typed tenant-authorized read tools |
| 16 | Measured PostgreSQL queue decision; concurrency/heartbeat/fencing/shutdown |
| 17 | Durable owner-scoped conversations/checkpoints |
| 18 | Immutable proposals, explicit human decisions and atomic ticket execution |
| 19 | Coordination assessment; production multi-agent path not justified |
| 20 | Tenant Slack adapter/contract tests; live sandbox pending owner configuration |
| 21 | React/TypeScript login/protected shell and memory-only token strategy |
| 22 | Conversation/RAG UI, citations and authorized preview |
| 23 | Admin records/quality/queue UI |
| 24 | Execution history and explicit approve/execute UI |
| 25 | HTTP/privacy limits, threat model and dependency remediation |
| 26 | Reproducible benchmarks and bounded opt-in BM25 index cache |
| 27 | Native ARM64 full local containers/migrations/proxy/outage/restart verification |
| 28 | Offline CI and unexecuted AWS runbook/manual readiness; no resources created |
| 29 | Real browser/fault journeys; conversation JSON and live-metric wiring fixes |
| 30 | Verified README/architecture, synthetic demo, operations/API/interview handoff |

Daily commands, results, limitations and commit context remain in
IMPLEMENTATION_STATUS.md and learning-journals/. No remote push or cloud success
is inferred from a local milestone commit.
