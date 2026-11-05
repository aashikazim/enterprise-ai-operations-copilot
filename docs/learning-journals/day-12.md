# Day 12 — tenant-safe evaluation and queue monitoring

Date: 2026-11-05. Status: implementation verified with synthetic PostgreSQL data.

## Design

Extend existing routers with tenant-admin summary/list/metrics APIs. Use SQL
aggregation instead of loading full payloads. Current queue states/ages are
all-time; completed/verdict/retry and RAG metrics use a bounded time window.
This prevents an old stalled job disappearing when the window advances.
Malformed historical `claims` JSON contributes no verdicts rather than failing
the entire summary. Lists cap limits/offsets and order by time plus ID.

Existing RAG metric storage is not automatically populated. Summary fields
explicitly return null for empty latency/rate populations. Queue results remain
useful independently. Prometheus-compatible text needs no new dependency.
Global in-process counters require an independent operator secret; tenant admin
privilege does not permit cross-tenant totals. Labels have fixed enums.

Retention is a documented policy, not an unapproved delete job. Payloads include
evidence and can be sensitive; suggested demo retention is 30 days after terminal
completion, subject to approved tenant policy and backup/provider retention.

## Verification

Targeted command from backend:
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_monitoring.py -q -p no:cacheprovider --tb=short`

10 passed in 2.07s. Tests cover exact percentiles/rates, tenant exclusion before
aggregation, stalled leases, empty/windowed data, malformed result JSON,
pagination, admin/operator authorization and no raw payload in responses.
No new migration or dependency; full regression result is in implementation status.

## FDE interview questions

1. **Why scope before aggregation?** Filtering after grouping leaks foreign
   tenants and corrupts their metrics; SQL scopes every population first.
2. **Why separate operator and admin metrics?** Tenant admins may inspect their
   own queue, not global totals. A dedicated token grants explicit operator access.
3. **Why null rather than zero?** No measurements is different from a measured
   zero latency or failure rate. It prevents misleading dashboards.
4. **How do you spot stalled work?** Oldest running age and expired lease counts
   expose claims that lack completion even outside the selected window.
5. **Are metrics an audit log?** Process counters reset and can miss crashes.
   Durable job states and separate approved audit records serve that purpose.
6. **Why not delete old evidence now?** Retention can conflict with customer holds
   and backup policies. Define access/retention first and authorize destructive cleanup.
