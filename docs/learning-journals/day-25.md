# Day25 — security hardening and negative tests

Date:2026-11-05. SECURITY.md maps trust boundaries and remaining risks. Add
bounded HTTP input, safe response defaults, validation privacy, generic error
sanitization, whitespace question rejection, ingest limit and safe SMTP logging.
Preserve Swagger/Redoc behavior; do not silently break docs with an API CSP.
No CORS expansion or auth architecture replacement. Existing adversarial tests
cover tenant/tool/approval/checkpoint boundaries; new tests add JWT/header/body/
log/privacy/rate cases. A Git-visible secret guard suppresses matched values.

Dependency audits were executed, not assumed. Npm initially flagged6packages;
same-major router/Vite patches plus a fixed major development-test-runner release
reduced findings to0. All17frontend tests/build passed after upgrades. Isolated
pip-audit found12findings in pip24.0; installer26.2fixed them, with no known
remaining findings or skipped packages. Docker bootstrap updated accordingly.
Secret scan0findings. Full regression and exact counts in implementation status.
No schema change, production mutation, live connector read or paid model call.

## FDE interview questions

1. **Why sanitize validation?** Default errors can echo submitted passwords or
documents even when application handlers avoid logging them.
2. **Why cap HTTP and ingest separately?** Transport bytes and semantic document
size defend different resource paths; neither alone bounds every workload.
3. **Does zero audit findings mean secure?** No. It is a current advisory snapshot,
with image, runtime and logic risks still requiring review.
4. **Why keep secret scan output minimal?** Printing a candidate secret would
create another disclosure in the very tool intended to prevent it.
5. **Why not introduce cookies now?** Preserve existing auth while using memory
JWTs; a cookie/session redesign requires CSRF and lifecycle work, not a quick swap.
6. **What is the key residual risk?** Application-only tenancy, model/privacy
limits, missing distributed limits and unverified deployment/provider controls.

Modern pip check exposed an existing cuSPARSELt0.8.1 embedded SBSA tag. Downloaded
and reinstalled the official same-version aarch64 wheel; its internal tag has
the same upstream issue. PyTorch import, CPU tensor sum8.0 and CUDA detection
passed. Retain this explicit packaging-check warning rather than rewriting
vendor metadata.199backend tests passed in40.19s before the same-version wheel
reinstall;7security targets passed in2.13s. No model inference claim.
