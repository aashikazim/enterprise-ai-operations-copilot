# Operations Copilot frontend

React/TypeScript/Vite; Node>=22.12. Local-only: no hosted Site registration or
publication. Existing backend routes and package structure remain intact.

```powershell
cd frontend
npm ci
npm test
npm run build
npm run dev
```

API runs separately on loopback8000. Vite proxies /api and strips that prefix.
Optional server-only API_PROXY_TARGET in frontend/.env configures the dev proxy.
Never put secrets in VITE_variables, which are public browser inputs.

Optional Docker dev stack:
`docker compose -f docker-compose.yml -f docker-compose.frontend-dev.yml up --build`.
The development Node image tag is moving; production pins/runtime verification
follow the deployment milestone. No dev-container startup was performed here.

## Authentication decisions

Existing invitation-only users sign in. Tokens live only in React/client memory,
never localStorage/sessionStorage/URLs. Reload/sign-out clears this client;
a stolen token remains valid until backend expiry because revocation/refresh
is not implemented.401clears client state. No cookie credentials are sent;
Bearer headers target same-origin /api. Backend authorization remains mandatory.
React escapes text; no raw HTML rendering. Tests use mocked HTTP. Browser visual
QA is separate from unit/build verification.
