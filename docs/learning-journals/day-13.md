# Day 13 — safe request-to-worker tracing

Date: 2026-11-05. Status: partial, collector smoke blocked by Docker permissions.

## Architecture and decisions

Use OpenTelemetry API/SDK and OTLP HTTP export. Explicit spans complement
existing timing logs instead of globally instrumenting SQL/HTTP clients, whose
default metadata can contain customer data. A small attribute allowlist permits
only opaque IDs, methods, route templates, status codes, attempts and queue wait.
Trace error status is set without exception description/stack events.

An additive nullable JSONB trace carrier plus optional unique request UUID
preserves old jobs. Store only traceparent, never arbitrary baggage/tracestate.
Worker spans restore its parent after claiming and carry final-attempt details.
This follows official [manual instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/)
and [propagation](https://opentelemetry.io/docs/languages/python/propagation/)
patterns, with stricter application privacy boundaries.

Default-off tracing exports nothing. When enabled with no endpoint, spans remain
local with no network dependency. Configured export uses asynchronous batches
and a two-second exporter request timeout; caller startup does not require a
collector. Only configured HTTP(S) URLs without credentials/query are accepted.
Proxy environment inheritance is disabled for exporter requests.

## Verification and blocker

Dependency plan was resolved before installation. SDK/HTTP exporter 1.45.1
matches existing API 1.45.1; requirements preserve original UTF-16 encoding.
`pip check` passed. Tests from backend:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_tracing.py tests/test_migrations.py -q -p no:cacheprovider --tb=short
# 9 passed in 0.72s
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/ -q -p no:cacheprovider --tb=short
# 124 passed in 11.67s
```

Tests use real isolated PostgreSQL, actual SDK in-memory export and mocked model
responses. They verify inherited parent IDs through persistent jobs, provider
spans, payload/JWT/baggage exclusion, sanitized error status, invalid parents,
disabled/no-collector mode and the full migration chain.

Official image manifests include ARM64 for collector 0.147.0 and Jaeger 2.5.0.
Compose configuration validation succeeded. Starting only these two services in
the `copilot-tracing-check` project failed: permission denied on
`/var/run/docker.sock`. No service started and no broad permission change was
attempted. Live export/Jaeger inspection remains pending; test results must not
be presented as proof of that deployment.

## Exact resume steps

1. Owner restores Docker access for this execution session or explicitly
   authorizes an appropriate narrow elevated Docker command.
2. From repository root, validate Compose and start only test tracing services:
   `docker compose -p copilot-tracing-check -f docker-compose.yml -f docker-compose.tracing.yml up -d --no-deps jaeger otel-collector`.
3. Emit a synthetic trace from the installed backend SDK to
   `http://127.0.0.1:4318/v1/traces`, force-flush and confirm it appears in
   Jaeger at loopback port 16686. Do not use customer content or paid calls.
4. Stop only the test-project tracing services. Record actual outcome, commit
   verified Day 13 completion, then begin Day 14 bounded read-only LangGraph.

## FDE interview questions

1. **Why carry context durably?** Threads/processes do not share trace context;
   the job record is the explicit handoff between request and worker.
2. **Does traceparent authenticate a tenant?** No. It is untrusted diagnostic
   correlation; JWT/user context and DB filters enforce authorization.
3. **Why avoid automatic exception events?** They can serialize SQL parameters,
   prompts or provider messages. Fixed error status is safer.
4. **What does no collector mode do?** It lets core services run independently.
   It does not guarantee trace persistence or a working external backend.
5. **How do retries appear?** Each reclaimed attempt has its own worker span
   under the original request, annotated with attempt count and queue wait.
6. **Why pause on daemon permissions?** Broad socket/group changes expand host
   privileges. A failed runtime check is documented until explicitly resolved.

## Runtime check completed after access restoration

Owner restored Docker group access. Used `sg docker` for this process's stale
group list; did not change host permissions. Docker 28.3.3 started the two
isolated ARM64 test services. SDK force_flush returned True; Jaeger returned
the exact synthetic trace and smoke.synthetic span. Both test services were
stopped afterward. Day 13 is now completed; previous blocker notes are retained
as debugging history.
