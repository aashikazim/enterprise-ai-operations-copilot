# Reproducible local deployment

This extends the original Compose layout. PostgreSQL data remains in the
project's `postgres_data` volume. Never run `down -v` against a development or
production project. Use a distinct project name/ports for a clean smoke check.

## Linux and PowerShell

Copy `.env.example` to `.env` (`cp` on Linux, `Copy-Item` in PowerShell). Set
independent URL-safe random POSTGRES_PASSWORD and JWT_SECRET_KEY values locally.
Never paste them into chat or commit them. Use the documented loopback bindings.
The original base file's LAN default is preserved for compatibility; the example
environment deliberately overrides it to `127.0.0.1`. A blank OpenAI key permits
auth/records/admin operation; grounded generation requires owner configuration
and local embedding/reranker model downloads. Evaluation remains opt-in and may
incur provider charges. Do not enqueue live evaluations without cost approval.

```sh
docker compose -f docker-compose.yml -f docker-compose.deploy.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.deploy.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.deploy.yml ps
curl http://127.0.0.1:8000/ready
# PowerShell: Invoke-RestMethod http://127.0.0.1:8000/ready
docker compose -f docker-compose.yml -f docker-compose.deploy.yml logs --tail 30 migrate
# Open http://127.0.0.1:8080 ; API calls use same-origin /api/ proxy.
docker compose -f docker-compose.yml -f docker-compose.deploy.yml down
```

`migrate` provisions vector, then upgrades Alembic to head before API/worker
startup. It never downgrades or deletes rows. Back up existing databases first;
review migration SQL before production upgrades. For cloud DBs provision vector
with an administrator, then use a separate least-privilege app role. The simple
local setup still shares a provisioning-capable role: not a production RBAC claim.
Do not run two migration services concurrently. Schema rollback requires reviewed
backup/restore planning, not an automatic downgrade on live data.

The API and worker run as UID10001; the static frontend uses unprivileged Nginx.
There are health/dependency checks, resource limits and SIGTERM grace periods.
Worker liveness is container/process based; use queue age/throughput metrics to
detect stalled processing. Model downloads are cached in a persistent volume.
Image build installs pinned Python packages but base image tags remain moving;
release deployments should pin reviewed digests and scan OS layers. API/DB are
loopback-published for local troubleshooting; cloud networking must be private.
No TLS is supplied locally. Never expose this developer stack directly online.

## ARM64 and model constraints

Build natively on ARM64 or AMD64; do not force an AMD64 platform on DGX Spark.
Python3.12, Node22 and unprivileged Nginx multiarch images are used. Python model
packages make the backend image large. Default Docker execution does not expose
GPU devices; CPU execution remains available. GPU passthrough needs a compatible
host NVIDIA Container Toolkit and separately verified runtime configuration.
See SECURITY.md for the installed NVIDIA SBSA wheel metadata warning. A successful
container health check does not prove real-model download/inference or paid API
availability.

## Optional tracing

Add `-f docker-compose.tracing.yml` for the collector and Jaeger. Its ports bind
loopback. Configure the worker exporter using the same OTLP HTTP endpoint when
needed. Traces contain allowlisted metadata, never raw prompts/documents/tokens.
Jaeger local storage is not a durable compliance archive.

With an empty provider key the worker stays alive but waits without claiming
jobs. Configure credentials locally and restart it before live evaluation.
This prevents an offline deployment from exhausting queued jobs' retry budgets.

Read-only proxy/security smoke: `python3 ops/smoke_http.py http://127.0.0.1:8080`
(PowerShell: `py ops/smoke_http.py http://127.0.0.1:8080`). This checks SPA routes,
health/readiness and unauthenticated denial, not real-model generation.
Nginx re-resolves Docker DNS after backend container replacement rather than
retaining a stale IP. See the official [proxy_pass behavior](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass).

## Verified local evidence (2026-11-05)

An isolated `copilot-day27` project built and ran natively on ARM64 using separate
ports15439/18080/18081 and freshly created project volumes. Migration reached
`1a18a0000001`, vector0.8.7 and33indexes; API UID10001 had writable model cache.
SPA/proxy/health/401/security-header checks passed. Initial worker startup with
no key and stale Nginx upstream IP failed; both were fixed and repeated checks
passed. Injected DB stop returned readiness503; reconnect returned200. Backend
replacement recovered through Docker DNS. Full stop/start retained volumes and
passed health gates. No development DB reset, real model download/inference,
paid API call, cloud deployment or image OS vulnerability scan was performed.
