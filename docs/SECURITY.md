# Security review and remaining risks

Reviewed2026-11-05. Portfolio prototype; no certification or production-readiness
claim. Threat model includes untrusted users/documents/model output and tenant
boundary probes, not a fully privileged database/host operator.

|Boundary|Implemented control|Evidence / limitation|
|---|---|---|
|JWT identity|Signed configured algorithm, active DB user, role/tenant recheck|Unsigned-token/revocation tests; no token refresh/revocation list|
|Invitation/login|Invite-only single use, hash/expiry,5/min login guard|Auth/invitation/rate tests; limit is process-local|
|HTTP|1MiB body cap;100k-character text ingest cap;safe validation/errors|Body/input/error tests; not a slow-client/concurrency defense|
|Tenant data|Filters before dense/BM25/tool/source/job/admin reads|Cross-tenant negative tests; no DB RLS defense against privileged SQL|
|Graph/memory|Fixed routing/budgets; owner+tenant checkpoints; run-token leases|Restart/resume/fencing tests; cooperative local-node deadline|
|Writes|Immutable API proposals, explicit admin approve+execute, preconditions|Concurrency/replay/revocation/tamper tests; local DB writes only|
|Connectors|Tenant-specific secret/channel allowlist;fixed HTTPS/no redirects|Mock contracts; live Slack pending; no webhooks/writes|
|Browser|Memory-only JWT,escaped React text,same-origin proxy|Interaction tests; XSS can access a live session; reload signs out|
|Telemetry|Safe attribute allowlist,no prompts/SQLparams/exception events|Trace/log privacy tests; collector requires operational access control|
|Retention|Owner deletion,logical conversation expiry,evaluation default-off|Physical cleanup/backup/provider retention remain owner policy|

HTTP responses set nosniff,frame denial,no-referrer,no-store and restrictive API
CSP. Swagger/Redoc retain their existing scripts; their CSP is not locked down by
this API middleware. Production frontend CSP/TLS/reverse-proxy limits are part
of deployment. CORS is not widened. Validation errors omit Pydantic input/context
that can echo passwords/documents. SMTP and generic HTTP failures log fixed safe
messages. Customer content is still legitimately sent to the configured model;
obtain tenant/provider authorization before using sensitive data.

## Dependency and secret checks

- Initial npm audit:6affected packages(1moderate,3high,2critical). Updated router
7.18.5,Vite7.3.7 and Vitest5.1.0; final npm audit:0known vulnerabilities.
- Isolated pip-audit2.10.1 inspected installed backend metadata. Initial12known
findings were in pip24.0; upgraded only the installer to26.2.0. Docker bootstrap
also pins that installer. Final pip-audit:no known vulnerabilities; no skipped
packages. This is an advisory-database snapshot, not proof of absence of flaws.
- `python backend/scripts/check_secrets.py`:0potential findings. It scans Git-visible
text and reports file/line/rule only, excludes ignored data/environment files,
and never prints candidate values. It is heuristic, not a full history scanner.
- Docker OS/image vulnerability scanning, real provider authorization, TLS hosting
and broad adversarial penetration testing remain unverified.

## Repeat checks

```powershell
cd frontend
npm ci
npm audit --audit-level=low
npm test
npm run build
cd ..
backend/.venv/bin/python backend/scripts/check_secrets.py
```

On Windows use backend\.venv\Scripts\python.exe. Install pip-audit in a separate
tooling environment and audit the application's installed site-packages with
`--path`; do not install audit dependencies into the production environment.
Never paste keys/JWTs/customer documents into issue reports. Rotate a disclosed
credential outside Git and inspect history before any public release.

## ARM64 installer metadata exception

Modern pip check reports nvidia-cusparselt-cu13 0.8.1 unsupported on this platform.
Inspection confirmed the official aarch64 wheel contains Tag:py3-none-manylinux2014_sbsa.
A same-version official ARM64 reinstall did not change that tag. PyTorch2.14.1+cu130
imports, CPU tensor multiplication(sum8.0) and CUDA detection passed afterward.
Do not edit vendor metadata or claim pip check clean. No dependency-version
conflict was reported; packaging compatibility remains an upstream ARM64 issue.
Runtime/model inference and image vulnerability verification are separate.
