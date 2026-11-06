# Day 15 — enterprise read tools

Date:2026-11-05. Status:completed. Preserve existing models/endpoints; add
`tool_service.py` with immutable specs, typed Pydantic args, allowed roles,
50-row cap and1000ms PostgreSQL statement timeout. Independent sessions recheck
active user and filter tenant before reading. Logs omit args/content. Registered
names cannot dispatch arbitrary functions or SQL. Agent exact-read routing
returns metadata without another LLM call. Writes remain unavailable.

Targeted20passed in4.41s; regression144passed in15.88s using the commands in
IMPLEMENTATION_STATUS.md. Fixed a Mock/MagicMock test-double mistake. Tests
cover foreign IDs, malformed/tenant args, denied write names, revoked users,
injected record text and sanitized query failures. No dependencies/migrations.

## FDE interview questions

1. **Why a registry?** Make schemas, role policy and bounds explicit rather
than executing arbitrary model-selected code.
2. **Where is tenant identity?** Verified user context, rechecked server-side;
never accepted from model/tool args.
3. **Why foreign IDs return404?** Avoid leaking cross-tenant record existence.
4. **What does timeout cover?** SQL execution only; connection pool checkout
has separate limits.
5. **Can prompt injection invoke a write?** Content is data and no write tool
exists. An admin role alone does not add unregistered capabilities.
6. **How will writes work?** Persist immutable proposals, require human approval,
recheck permissions and fence execution (Day18).
