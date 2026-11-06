# FDE architecture pitch and interview preparation

## Ninety-second pitch

This operations copilot connects enterprise knowledge and tickets under a
server-enforced tenant identity. Dense and BM25 retrieval fuse and rerank evidence
before generation; numbered citations make it inspectable. A bounded LangGraph
adds typed record reads and durable conversations without replacing the original
RAG endpoint. Ticket writes become immutable proposals: an authorized human
approves, then explicitly executes a revalidated atomic transaction. Sampled
claim evaluation runs on a durable PostgreSQL queue, independent of request
transactions. Operators see safe aggregates/traces and admins use a React UI.
Native ARM64 containers and a real-browser synthetic journey are locally tested.
Live provider quality, Slack sandbox and AWS execution remain explicit limits.

## Questions and defensible answers

1. **Why PostgreSQL rather than Celery?** Existing status/leases share transactional
   storage. A controlled40-job mocked benchmark measured concurrency benefits;
   a second queue lacked a demonstrated requirement. Routing/scheduling at scale
   could justify a later migration, with one durable source of truth.
2. **What is at-least-once?** An expired lease can repeat a provider call. Attempts
   fence stale completion; idempotent ticket execution is local/transactional,
   not a claim that model or future external effects run exactly once.
3. **How does tenant isolation work?** Verified JWT→active DB user→tenant/role;
   predicates at chunks/documents/tools/jobs/history/approvals/admin/connector.
   Authenticated browser foreign-ID probe returns404. Application filters are
   not database RLS or protection from a compromised DB administrator.
4. **Why BM25 plus dense?** Exact identifiers and semantic similarity complement
   each other; RRF avoids direct score-scale comparison. Cross-encoder reranks.
   Identifier fixtures do not establish broad semantic recall.
5. **What do citations prove?** Number validity/order, not claim support. Claim
   assessment is separate; synthetic evaluator outputs are not real accuracy.
6. **How isolate request failure?** Enqueue/metrics use separate short transactions;
   failures are sanitized and cannot commit/rollback unrelated caller work.
7. **How protect tools?** Typed bounded args, fixed registry, active user/tenant
   checks, SQL timeout and explicit human gates. Retrieved text grants no authority.
8. **How resume safely?** Durable owner-scoped checkpoints, run token/lease fencing,
   bounded untrusted history, explicit manual resume. No unsafe pickle fallback.
9. **What broke during implementation?** Checkpoint pending-write ordering; approval
   datetime JSONB storage; no-key worker startup; stale Nginx upstream IP; mobile
   metrics overflow. Each was reproduced and fixed with meaningful verification.
10. **What did caching improve?** One local repeated200-chunk BM25 workload p50
    6.964→4.415ms. Fresh tenant SQL remains. Default-off8-entry content-keyed cache
    trades memory retention for computation; no production/RAG speedup is claimed.
11. **How control costs?** Default-off sampled evaluation, bounded graph/provider
    retries and worker concurrency. Usage/cost stay null until actual provider
    telemetry is available. Cloud budget/region approval precedes resource creation.
12. **What is production-oriented versus production verified?** Local limits,
    permissions, queues, tests and runbooks are implemented. TLS, managed secrets,
    backups/restore, cloud IAM, live integration and sustained load require actual
    deployment/measurement. No certification or AWS success is claimed.
13. **Why no coordinated agent deployment?** Same-policy synthetic assessment found
    no correctness benefit. Additional roles need measured task improvement, not
    framework complexity for a portfolio checklist.
14. **What would you do next?** Approved live Slack/provider validation, broader
    labeled semantic evals, usage telemetry, durable retention cleanup policy,
    sustained load and reviewed cloud IaC after explicit billing authorization.
