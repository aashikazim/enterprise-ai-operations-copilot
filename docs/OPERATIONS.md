# Local operations and troubleshooting

## Startup and schema

Use the full Compose pair from DEPLOYMENT.md. `migrate` must exit0 before API and
worker start. Current head:1a29a0000001. The additive Day 29 migration permits
unknown token/cost fields; it does not rewrite applied history. Its downgrade
will fail if null records exist: review/export data rather than invent values.
Never run fixture resets or automatic downgrades on development/production.

Readiness (`/ready`) checks DB; `/health` checks process only. Frontend static
health does not establish API/provider health; run ops/smoke_http.py through the
proxy. On a replaced API container, Nginx re-resolves Docker DNS within5seconds.

## Queue and evaluation

Evaluation is off by default. With approved provider/data configuration, enable
RAG_EVAL_ENABLED and a 0..1 sample rate; restart API/worker to reload settings.
Use tenant-admin `/rag/monitoring/summary` and paginated `/jobs` to inspect pending
age, running leases, retries, throughput and failures. Operator `/metrics` needs
a separate token; do not put tokens in URLs/logs. Increasing worker concurrency
from 1 up to 8 is supported but must respect provider limits and DB capacity.

An empty key makes the worker idle without claiming. Configure the key and
restart; don't delete queued jobs to hide missing credentials. Repeated auth or
malformed-payload errors are terminal; transient failures retry with bounded
backoff. Investigate sanitized outcome codes. Never edit attempts/lease fields
while another worker owns a job. Delivery is at-least-once; a provider call may
repeat after crash, while stale attempts cannot publish completion.

SIGTERM stops claims and drains current work. Compose grace75seconds exceeds the
configured provider60second timeout plus short completion work, but network/DB
stalls can still exceed it. A forced kill relies on lease recovery. Do not call
this exactly-once LLM execution. Heartbeats use independent sessions.

## Answers and conversations

No evidence yields abstention. Invalid numbered citations yield abstention;
valid numbers do not prove factual support. Real semantic evaluation requires
provider execution and labeled examples. Missing model cache triggers downloads;
health remains independent. Model loading is not hard-cancellable by browser.

Stop waiting aborts only browser wait. Refresh an authorized conversation before
retrying; use explicit resume for interrupted runs. Runs carry120second leases
and checkpoints; stale writes are fenced. Conversation history is bounded to
10 messages/4000UTF-8bytes as untrusted text. Logical expiry30days does not perform
physical erasure. Owner DELETE rejects active runs and cascades conversation data.

## Approvals and records

Approval expiry15minutes; approve does not execute. Reinspect target and explicit
execution state before resubmitting after network failure. Executed replay is
idempotent. Changed tickets, altered arguments, revoked approvers or expired
proposals fail safely. External mutating tools are not implemented.

Demo seeding refuses overwrites; if seed data exists, use the existing records
and your chosen account. Password resets are an owner operation; don't reset DBs
as a shortcut. SMTP onboarding needs owner configuration and actual delivery
verification; no email was sent during these milestones.

## Backups, retention and security

Back up PostgreSQL using an authorized operator account; keep outputs outside
Git with restricted permissions and test restore into a separate local database
before trusting a backup. A successful pg_dump is not a verified restore.
Production snapshot/restore and TLS are unexecuted cloud-runbook tasks.

No automated destructive retention cleanup is configured. Follow
EVALUATION_DATA_POLICY.md for raw evaluation payloads and audit retention. The
optional BM25 cache retains raw text until eviction/restart; leave it off where
immediate erasure is required. Environment secrets aren't an encrypted vault.
Audit npm/Python and image OS layers on release; current advisory snapshots are
not a certification. Do not suppress the upstream NVIDIA SBSA tag warning by
editing vendor metadata. SECURITY.md records its current practical limits.

## Test failures

Run reset-based suites serially; confirm both allowlisted test DBs are disposable.
Connection errors inside a restricted sandbox do not establish code regressions;
retry with approved local DB access. Missing Playwright browser: install Chromium
or point BROWSER_EXECUTABLE_PATH at a supported local browser. A browser failure
must remain a failed test until reproduced/fixed, not be silently skipped.
