# ADR 001 — retain and scale the PostgreSQL evaluation queue

Date:2026-11-05. Decision:retain PostgreSQL; no Redis/Celery introduced.

The system already stores job payloads/results and uses SKIP LOCKED, leases,
bounded attempts and tenant-safe status APIs. A second broker would add delivery
coordination and an outage mode without demonstrated need at this scale.

## Measurements

Repeatable synthetic workload:40 jobs, in-process mocked evaluator, actual local
PostgreSQL, one/four concurrent consumers. Command from backend:
`pytest tests/test_queue_scaling.py -q -s -p no:cacheprovider --tb=short`.

| Version | Workers | jobs/s | elapsed s | p95 queue wait s |
|---|---:|---:|---:|---:|
| Before hardening |1|101.54|0.394|0.381|
| Before hardening |4|278.56|0.144|0.139|
| After hardening |1|92.00|0.435|0.397|
| After hardening |4|275.41|0.145|0.134|

These single short runs characterize local queue overhead, not model throughput,
production capacity or statistically significant performance improvements. All40
jobs completed once per run with one attempt; no claim of exactly-once external
inference. Contention/lock behavior is exercised by simultaneous consumers;
database-wide production contention and paid API capacity remain unmeasured.

## Implementation and failure behavior

Configurable1–8 independent worker threads, default1, each with its own client
and sessions. No DB transaction spans a model call. Lease renewal uses a separate
short-lived session and fences by job/status/attempt/unexpired lease. Lost renewal
prevents writes by the worker. Completion/failure also rejects expired leases.
Graceful SIGTERM/SIGINT stops new claims and waits for in-flight attempts; worker
provider calls use60s timeout and no automatic retries. Network libraries cannot
provide an OS-level hard kill guarantee; size deployment shutdown grace suitably.

Malformed input/type errors and provider authentication/permission/bad-request
errors become terminal at the current attempt. Transient errors use existing
bounded retry/backoff. Crashes recover after lease expiry; duplicates remain
possible, with stale results fenced. No new queue source of truth.

Revisit Celery/Redis when measured DB contention, routing or independent task
scheduling justifies migration. Preserve PostgreSQL status/idempotency and use
an explicit delivery transition rather than dual-enqueueing the same job.
