# Slack sandbox setup and verification

Status:read-only adapter verified offline; live access pending credentials.
Official contracts: [history](https://docs.slack.dev/reference/methods/conversations.history/)
and [rate limits](https://docs.slack.dev/apis/web-api/rate-limits/), checked2026-11-05.
Provider account/app rate limits can vary; honor Retry-After rather than assuming
a fixed tier. No automatic write or webhook endpoint exists.

1. Owner creates/uses a sandbox Slack app, grants only the history scope needed
for intended public/private channels, installs in a sandbox workspace and invites
the bot only to permitted channels. No broad workspace permissions are assumed.
2. Keep tenant mappings locally in a protected secret file or deployment secret
manager. JSON shape: `{ "<tenant_id>": { "bot_token": "<sandbox_bot_token>",
"channel_ids": ["<allowed_channel_id>"] } }`. Each tenant has its own entry;
no global token fallback. File credentials/ is ignored. The adapter supports
bot tokens, not arbitrary user/session credentials.
3. PowerShell: `$env:SLACK_TENANT_CREDENTIALS = Get-Content -Raw .\credentials\slack-tenants.json`.
Linux: inject the mapping through your secret manager or backend.env configuration;
do not echo it or include it in command arguments/history. No example real token.
4. Restart the API. With the existing tenant JWT, GET the allowlisted history
endpoint with limit1. Inspect content privately. Verify another tenant/channel
is denied. Do not paste returned customer text or tokens into logs/reports.
5. Record only HTTP status, count and authorization outcomes. Remove/rotate
sandbox access when finished. No upload/posting verification is requested.

Read guard:1request/sec per configured tenant/process. Provider429 may retry
once only when Retry-After<=2s; longer waits return429.5xx retries once after
0.2s. Authentication/schema/redirect errors fail safely. Responses cap1MiB,
15messages,4000characters/message; truncated flags are explicit. Cursors are
bounded opaque data. Tokens appear only in Authorization to the fixed Slack
host. HTTP proxy/netrc inheritance and redirects are disabled.

No message content is persisted by the standalone history endpoint. If a human
uses a connector read in a conversation, its structured result can be retained
in the owner's graph checkpoint; apply conversation privacy/retention policy.
No actual sandbox data has been retrieved in the verification run.
