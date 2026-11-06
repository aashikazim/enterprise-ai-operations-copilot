# Day16 — queue scalability and recovery

Date:2026-11-05. Retain PostgreSQL; ADR001 contains baseline/after measurements.
Concurrent workers completed all40 synthetic jobs once at1/4consumers. Mocked
model cost/latency is excluded. Add configurable concurrency, lease heartbeat,
expired-write fencing, poison-job handling and signal-driven graceful drain.
No new dependency/migration. Unit/integration tests include heartbeat over a
short lease, stale renewal/completion, restart claim recovery, terminal input
failure and stop-before-claim. Changed the Day11 transient-error fixture from
ValueError to RuntimeError because malformed ValueError is now permanent.

Targeted34passed in5.01s, with before/after output recorded in ADR001. Full
regression result is recorded in IMPLEMENTATION_STATUS.md. No paid API calls.

## FDE interview questions

1. **Why retain PostgreSQL?** Existing durability and measured local capacity
meet the demonstrated need; another broker adds coordination and operations.
2. **What prevents duplicate inference?** Nothing guarantees exactly-once across
crashes. Lease renewal reduces duplicates; fencing prevents stale writes.
3. **What happens when renewal fails?** Stop publishing that attempt's result;
lease expiry allows recovery without a stale worker overwriting newer work.
4. **Why classify poison jobs?** Repeating malformed/auth-denied requests wastes
attempts and provider cost without a reasonable recovery path.
5. **How does shutdown work?** Signal an event, stop new claims, drain in-flight
workers and retain leases during their work. Deployment grace must allow it.
6. **What does this benchmark prove?** Local queue overhead and basic concurrency;
not real LLM throughput, production scale or statistically significant gains.
