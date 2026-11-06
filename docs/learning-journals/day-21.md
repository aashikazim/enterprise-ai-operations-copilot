# Day21 — React/TypeScript foundation

Date:2026-11-05. No frontend existed. Add frontend/ with React19/TypeScript5.9/
Vite7 and typed API client, routing, accessible login/error/loading states and a
responsive protected shell. Existing JWT login retained; additive /auth/me omits
password hashes. Tokens remain in memory; no refresh, persistent storage or
cookie credentials. Same-origin proxy avoids widening CORS. Sites local-only
workflow applied without registration/publication. Optional Docker dev override
provided; container runtime/visual QA not claimed at this milestone.

4frontend tests and TypeScript/Vite production build passed. Backend identity
check1passed in0.33s; full regression in implementation status. No migration or
paid call. Tests verify protected route, login/logout, sanitized failure,
401clearing and no local/session storage.

## FDE interview questions

1. **Why memory tokens?** Compatible with Bearer APIs while avoiding persistent
browser token storage; reload requires sign-in.
2. **Does logout revoke JWTs?** It clears this client only. Server expiry remains
the boundary until revocation is implemented.
3. **Why same-origin proxy?** Explicit credential destination and no permissive
cross-origin policy.
4. **Do hidden admin links authorize?** No. Backend enforces role/tenant on every
request; frontend visibility is convenience.
5. **What did tests/build prove?** Typed code and mocked contracts, not live
provider deployment or complete browser visual QA.
6. **Where do secrets belong?** Backend secret configuration; never public
VITE_variables or frontend source.
