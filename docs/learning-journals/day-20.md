# Day20 — tenant-bound enterprise sandbox adapter

Date:2026-11-05. Offline implementation verified; live sandbox check pending.
A ReadConnector protocol complements the existing backend, with a fixed-host
Slack history implementation. Per-tenant SecretStr configuration and channel
allowlists derive from authenticated identity. No unchecked URL/tenant/token
request argument. Existing tools and publishing behavior are unaffected.

18offline HTTP/API/graph tests passed in0.87s; full187passed in35.37s. Tests
cover token/header scoping, foreign channels, schema/size/pagination, bounded
rate retry, no redirect token forwarding, unconfigured mode and graph identity.
No actual Slack/Jira credential was available and no live read was claimed.
No migration/dependency. CONNECTORS.md records exact setup and verification.

## FDE interview questions

1. **Why per-tenant credentials?** A global token with caller-selected resources
can cross customer boundaries; each mapping has explicit channels.
2. **Why fixed URLs?** Avoid SSRF and redirect-based token exfiltration.
3. **Why read-only first?** Prove access/contract safely before introducing
external mutation and uncertain-outcome reconciliation.
4. **How handle rate limits?** Small bounded retries for safe reads; honor long
Retry-After without holding a worker asleep indefinitely.
5. **Are env secrets encrypted?** No. They are local secret injection, not a
production vault; deployment must use appropriate managed secret storage.
6. **Does a mocked test prove live integration?** No. Live sandbox scopes,
permissions and provider behavior remain an owner-configured verification.
