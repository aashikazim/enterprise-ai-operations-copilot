# Day 27 — Reproducible local stack

Extended the original Compose layout with configurable ports, shared backend
image, one-shot additive migration service, worker and static React/Nginx proxy.
Python3.12 matches the verified host environment. App/worker UID10001 and
unprivileged Nginx avoid root runtime. Added health gates, resource limits,
model-cache volume, process init and graceful shutdown periods. Existing LAN
binding remains the base default; .env.example explicitly selects loopback.

Readiness checks PostgreSQL and returns only a fixed status. Vector provisioning
runs before historical migrations without editing their applied history.
Documentation distinguishes developer DB privileges from cloud least privilege.
Model dependencies make clean builds large; health does not establish inference.

## Interview questions

1. Why a separate migration process? One owner upgrades before consumers start.
2. Why preserve volumes? Deploying code must not destroy customer data.
3. Liveness versus readiness? Process health differs from DB availability.
4. Why same-origin proxy? Browser auth avoids broad CORS and persistent JWT storage.
5. How verify ARM? Build and run native images, not architecture-name assumptions.
6. Worker shutdown? Stop claims, drain current jobs within bounded grace.
7. Remaining production work? TLS, secrets, private networking and reviewed release digests.

Verification found two real runtime defects: empty provider credentials crashed
the worker, and Nginx held an old upstream IP after API replacement. The worker
now waits without claiming jobs, and the proxy resolves Docker DNS dynamically.
8targeted tests passed in3.48s; final regression204passed in39.98s;17frontend
tests/build passed. Native ARM64 fresh migration/vector/indexes, HTTP smoke,
DB outage/reconnect and backend replacement checks passed. Details in DEPLOYMENT.md.
