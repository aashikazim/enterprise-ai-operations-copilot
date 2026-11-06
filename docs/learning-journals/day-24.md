# Day24 — reviewable execution and approval UI

Date:2026-11-05. Actions/history view displays owner conversation steps/results
with actual turn timestamps and tenant-authorized approval details/audit events.
Proposals show target, expected/current status, proposed effect and expiry.
Admin actions require explicit confirmation; approval never auto-executes.
Execution requires a fresh confirmation. Regular users see no mutation controls;
backend authorization remains decisive. Busy/ref guards block duplicate clicks.
Stale detail requests abort, failures do not retry writes, and server conflicts
ask the user to refresh. Existing backend approval fencing is reused.

Added bounded status filter to approval list API.12backend targeted tests passed
in5.09s;17frontend tests and build passed. Fixed a test query matching both an
expired badge and filter option. Full regression in implementation status.
No new dependency/migration/paid call. Per-node timing was not invented: UI
labels actual persisted turn/audit timestamps rather than pretending node times.

## FDE interview questions

1. **Why two confirmations?** Reviewing a proposal and applying a mutation are
separate human decisions; UI must not quietly combine them.
2. **Can button disabling prevent replay?** It helps UX only. Backend row locks,
state checks and idempotent terminal replay provide the real guarantee.
3. **How handle stale approval?** Show expiry/preconditions, refresh detail and
let the server reject changed permissions/target state.
4. **Why abort stale detail requests?** Prevent a late response replacing the
proposal the user intended to review.
5. **What timestamps are shown?** Persisted turn and audit times, not fabricated
per-node execution timing.
6. **How handle action errors?** Safe feedback, clear confirmation and manual
refresh; never automatically resubmit a state-changing request.
