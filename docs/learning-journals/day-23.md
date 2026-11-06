# Day23 — tenant admin and quality dashboard

Date:2026-11-05. New admin metadata router exposes paginated document/ticket/user
views with require_admin and tenant predicates before query execution. Password
hashes, document bodies and ticket descriptions are excluded. Existing CRUD and
monitoring APIs remain. React Administration reuses Day12 aggregate APIs, renders
accessible tables, null measurements, queue health and failed-job summaries,
filters/pagination, and an explicit admin text-ingestion form.

Frontend hides navigation for regular users but does not provide authorization;
backend checks every request. Stale requests abort and old records clear while
filters reload. An initial test expected one empty table where there are two;
fixed the query to assert both expected empty states.

12frontend tests/build passed; admin target2passed in0.94s. Full regression is
in implementation status. No dependencies/migration; provider calls mocked.
Metrics are recorded samples, not a fabricated live request population.

## FDE interview questions

1. **Why backend admin checks?** UI hiding is not security; attackers can call
APIs directly.
2. **Why reuse metrics APIs?** Keep definitions/tenant filters in one server
implementation rather than duplicating analytics logic in browser code.
3. **Why null metrics?** No measured population is different from zero latency
or perfect quality; show not measured.
4. **How limit disclosure?** Select only authorized metadata fields and cap rows;
never return hashes or private bodies in record summaries.
5. **What about changing filters?** Abort stale fetches and clear old rows so
the display cannot mislabel previous results under a new filter.
6. **Does a dashboard prove production health?** No. It exposes measured state;
alerting, live workloads and deployment verification are separate.
