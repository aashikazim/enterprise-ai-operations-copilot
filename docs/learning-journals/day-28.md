# Day 28 — Cloud readiness with explicit gates

Prepared a bounded ECS CPU API/worker, private RDS/vector, CloudFront/private S3,
ALB/TLS, Secrets Manager and CloudWatch proposal. It is not deployed. Region,
budget, data policy and IAM need owner approval before infrastructure changes.
No Terraform resources or cloud credentials were created. Local Compose remains
the executed deployment path. Official AWS/GitHub docs informed the runbook.

Offline CI uses guarded disposable DBs, regression/migration tests, frontend
checks, secret/advisory scans and configuration validation. Official action
v7 tags were resolved to pinned SHAs. Manual release readiness references a
protected environment, but the owner must configure actual reviewer settings;
YAML alone cannot enforce that account configuration. No AWS deployment step.

## Interview questions

1. Why no cloud success claim? Credentials, billing approval and execution absent.
2. Why private DB? Only app/worker/migration identities need network access.
3. Why OIDC? Short-lived scoped credentials avoid persistent repository keys.
4. Are budget alerts hard caps? No; provisioned services still incur costs.
5. Can code rollback reverse schema? Only compatible code; data rollback needs reviewed restore.
6. Does an environment field ensure reviewers? No; repository settings must be configured.
7. Does local Nginx DNS work on ECS? Not directly; cloud discovery is separate work.

Local gate:204backend passed in40.92s,17frontend/build passed, Compose config and
5HTTP smoke checks passed, npm/Python audits0known, secret scan0. Audit DNS failed
inside sandbox then passed with network; corrected an unsupported audit flag.
Hosted CI and account protection settings remain pending; no remote push.
