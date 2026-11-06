# Day17 — durable owner-scoped memory

Date:2026-11-05. Add Conversation, ConversationMessage, AgentCheckpoint and
AgentCheckpointWrite through additive migration1a17a0000001. A custom
BaseCheckpointSaver implements the installed LangGraph contract using existing
SQLAlchemy sessions and typed serializer without pickle fallback. No separate
schema manager/service or dependency is introduced. Every state read/write
validates owner/tenant/active user/run token and lease; short transactions only.

Conversation turns persist user/assistant records; explicit resume compiles a
new graph against the durable checkpoint. History is untrusted and capped at
10messages/4000UTF-8bytes. Expiry is logical30days, not silent deletion. Owner
DELETE is explicit and rejects an active lease. Resuming an uncertain model
request can repeat its cost; no automatic resubmit is performed.

## Debugging and tests

Initial normal turns failed because LangGraph can save pending writes before
its checkpoint future completes. A dedicated pending-write upsert table fixes
that ordering. The deletion conflict path also needed its own rollback/lock
transaction. Stopped two overlapping test processes I had launched; reran all
checks serially. Only the approved disposable migration database was reset
when the uncommitted prototype revision changed. Historical committed migrations
and development data were preserved. Final targeted7passed in2.74s; full result
is in IMPLEMENTATION_STATUS.md. Tests cover fresh graph restart/resume, expired
and foreign owners, context bounds, token fencing, delete cascade and migrations.

## FDE interview questions

1. **Why persist checkpoints, not just messages?** Messages preserve dialogue;
checkpoints also preserve pending graph work and execution state across restart.
2. **Why separate pending writes?** LangGraph persists task writes concurrently
with checkpoint creation; requiring a parent checkpoint row introduces a race.
3. **How do you fence a crash?** A new run replaces the lease token; old saver
transactions revalidate it while locking the conversation row.
4. **Is user history authoritative?** No. It is bounded untrusted context;
server identity/system policy remains separate.
5. **Does expiry delete data?** No. It denies access; physical retention requires
an approved cleanup policy or explicit authorized deletion.
6. **Does resume guarantee no repeat charge?** No. Unknown model outcomes can
repeat on an explicit resume; no automatic replay is claimed.
