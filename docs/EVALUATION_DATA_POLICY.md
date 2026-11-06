# Evaluation payload policy

Evaluation is default-off. Enabling it retains the question, final answer,
ordered evidence text and claim-level assessment in PostgreSQL. These may
contain customer content. Use synthetic data for demos; obtain the tenant's
data-processing authorization before model/provider use.

## Access

Job detail reads require authenticated matching tenant. Summary, pagination and
tenant metrics require a tenant admin and expose only aggregate/operational
fields. The operator `/metrics` endpoint is disabled unless a dedicated
`MONITORING_METRICS_TOKEN` is configured; it exposes process-wide content-free
enqueue counters, never tenant content. Keep it on a private network, use TLS
outside local development and rotate the token. JWTs are not operator tokens.

## Retention

For the synthetic local demo, the recommended payload retention is 30 days
after terminal completion; pending/running jobs must not be deleted by a
cleanup process. Production policy must reflect customer agreements, legal
holds, backups and provider retention. Database encryption and backup retention
are deployment responsibilities; no compliance certification is claimed.

No automatic deletion is enabled. A retention implementation needs an approved
tenant policy, dry-run counts, explicit operator authorization, tenant filtering,
terminal-state/age checks, bounded batches, tests and a separately approved
destructive operation. Until then, operators must control test datasets and
storage access. Application deletion would not erase provider copies/backups.

## Metrics definitions

- Current status/depth and oldest pending/running age include all jobs for the
  tenant, so an old stalled job is not hidden by the reporting window.
- Completion/verdict/retry/processing statistics use a bounded 1–720 hour window.
  Retries sum attempts beyond the first for jobs created in the window.
- Processing seconds measure final claim start to completion; they exclude
  previous failed-attempt time and do not imply provider-only latency.
- RAG percentiles/rates use persisted `rag_metrics`, not sampled jobs as a
  denominator. Live RAG metric persistence is still disconnected; an empty
  population reports null rates rather than invented zeros.
- Process-wide enqueue counters reset at restart and are not a durable audit
  trail. Labels have fixed outcomes/statuses; no tenant, prompt or request-ID
  label is permitted. Prometheus collection/storage is not deployed here.

Live aggregate metrics contain opaque request/tenant IDs, timings and answer flags;
unknown usage/cost are null. No raw question/answer/evidence is copied there.
Completed evaluations update aggregate faithfulness only for the same tenant and
request. Aggregate-write failure does not commit/rollback request work or change
the returned answer. Durations exclude metric persistence/enqueue overhead.
