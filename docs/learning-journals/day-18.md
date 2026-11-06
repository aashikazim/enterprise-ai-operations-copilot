# Day18 — human approval for ticket mutations

Date:2026-11-05. Add approvals/events with additive migration1a18a0000001.
Typed proposals store immutable tool args, expected ticket state, SHA256 digest,
requester/tenant,15minute expiry and scoped idempotency key. Graph creates only
a proposal and returns approval_required. Explicit admin approve/reject and
separate execute are durable equivalents of a graph approval boundary; no native
LangGraph interrupt is claimed. No model-selected write executes directly.

Execution locks proposal and ticket, rechecks current executor and original
approver permission, verifies digest/expiry/expected state, then atomically
commits the local DB mutation, terminal status and event. Concurrent calls
serialize; an executed replay returns the stored result without another event.
This transaction pattern is specific to local ticket writes; external writes
will need separate uncertain-outcome reconciliation and idempotency semantics.
Events have no update/delete API; privileged DB tamper resistance is not claimed.

Tests cover no mutation before both human actions, repeated proposals,
concurrent/replayed execution, rejection, expiry, cross-tenant/role denial,
modified payload/target, revoked approver and graph proposals. Exact results
and commands are in IMPLEMENTATION_STATUS.md. Paid APIs mocked; no production
mutation/deployment. No new dependency.

## FDE interview questions

1. **Why separate approval and execution?** It makes authorization explicit
and lets the server recheck current policy at the actual mutation boundary.
2. **What is approved?** Fixed tenant/requester/tool/args and expected target
state, not free-form future model behavior.
3. **How prevent double execution?** Lock the durable approval row and commit
mutation/status/audit in one local database transaction.
4. **What about stale approval?** Expiry, permission and target preconditions
are revalidated; a changed ticket causes terminal failure.
5. **Is a hash an audit guarantee?** It detects unexpected payload changes in
the application threat model, not a privileged actor changing data and digest.
6. **How does restart work?** Approval state lives in PostgreSQL, so another
process can inspect/execute it without replaying the graph or trusting memory.
