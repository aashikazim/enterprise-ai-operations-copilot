# Reliability and quality verification

All database test commands must run **serially**. Fixtures verify database name
and connection before resetting only `copilot_test_db`; migrations separately use
`copilot_migration_test_db`. Never point these fixtures at development/production.
Prepare both with `scripts.prepare_test_database` as described in README.

## Repeatable browser journey

Install backend requirements and `npm --prefix frontend ci`. Install Chromium:
`cd frontend` then `npx playwright install chromium` (Linux CI may need
`--with-deps`). The browser is a development dependency, not an application model.

Linux, from backend:

```sh
RUN_BROWSER_E2E=1 .venv/bin/python -m pytest tests/ -q -p no:cacheprovider
# Use a supported system Chrome instead of Playwright's bundled browser:
RUN_BROWSER_E2E=1 BROWSER_EXECUTABLE_PATH=/usr/bin/google-chrome .venv/bin/python -m pytest tests/test_browser_journey.py -q -s -p no:cacheprovider
```

PowerShell, from backend:

```powershell
$env:RUN_BROWSER_E2E = '1'
.\.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider
Remove-Item Env:RUN_BROWSER_E2E
```

Without opt-in, exactly the browser integration is skipped. CI enables it and
installs Chromium. Hosted CI execution remains pending push; local execution is
verified separately. Test owns loopback Vite/FastAPI servers and stops them in
finally blocks. Each HTTP request receives a distinct SQLAlchemy session. The
browser script refuses remote origins. Fixed synthetic credentials are confined
to the disposable test DB and must never be used for deployed accounts.

The journey uses real login/JWT, PostgreSQL, LangGraph/checkpoints, BM25+dense SQL,
ingestion, tenant filters, citations, tools, approvals, dashboard and worker
transactions. Embedding vectors, cross-encoder ranking, generation and evaluator
outputs are replaced at model seams. It is **not** a live provider/inference test
or a full Docker/browser deployment test. Native Docker startup/recovery was
verified separately in Day27. Browser Chrome156/Playwright1.65.0 ran locally.

## Verified journey and faults

| Boundary | Evidence |
|---|---|
| Login/protected routes/logout | Browser journey and frontend auth tests |
| Upload/retrieval/source preview | Browser ingestion, real SQL retrieval, citations |
| Cross-tenant source probe | Authenticated preview target replaced with foreign ID; HTTP404 |
| Memory/tool/approval | Multi-turn browser conversation, explicit approve then execute |
| Durable job completion | Browser RAG enqueues; real worker consumes with mocked evaluator |
| Admin/mobile | Real dashboard API rendering,390px no-overflow check,0page errors |
| LLM unavailable | test_agents.py, test_evaluation_submission.py: sanitized503/no enqueue |
| Worker failure/stale claim | test_queue_scaling.py, test_evaluation_queue.py: simulated expired lease/fencing/poison/retry |
| Missing credentials | Worker waits without claims, graceful shutdown test + container |
| DB outage/reconnect | Isolated Day27 container stop/readiness503/reconnect200 |
| API replacement | Native container replacement; proxy dynamically re-resolves DNS |
| Connector timeout/outage | test_connectors.py mocked HTTP, bounded retry/rate/allowlist |
| Malformed/oversized documents | test_security_hardening.py, existing knowledge tests |
| Revoked roles/tenant probes | test_approvals.py, test_conversations.py, test_tenant_isolation.py |

The browser initially discovered non-JSON datetime values in persisted approval
turn results. `jsonable_encoder` at the persistence boundary fixed it; a direct
records→proposal checkpoint regression now protects the behavior. A second
browser failure was a collapsed details locator; the test now explicitly opens
execution details. Neither failure was hidden or reclassified as a passing run.

## Fixed quality dataset

`tests/test_fixed_offline_quality.py` seeds three synthetic chunks, searches two
unique identifiers and checks one no-match abstention. Actual BM25 Recall@3=1.0,
MRR=1.0; generated fixture citations valid2/2; no-match abstention1/1. Browser
worker fixture returns faithfulness1.0, **not a measured evaluator accuracy**.
Real semantic recall, faithfulness, token/cost and live agent success need model
execution and a broader labeled dataset. Historical eval JSON is not promoted
as a newly verified result. PERFORMANCE.md provides local timing measurements.
Coverage percentage has not been measured; no coverage claim is made.

Day29 follow-up closed the previously documented disconnected live-metrics path.
RAG now writes aggregate timings/abstention/citation flags with an independent,
best-effort transaction; the worker updates matching tenant/request faithfulness
inside fenced completion. No question/document text enters this table. Token
usage/cost remain null because the current provider wrapper returns text only.
Additive migration1a29a0000001 relaxes only those three columns' nullability;
rollback with null rows requires operator review, never fabricated replacement
values. Recorded latency excludes metric persistence and enqueue overhead.
Browser now verifies request count1 and mobile layout with real metric values.
