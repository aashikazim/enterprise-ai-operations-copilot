# Day 29 — Real browser and fault boundaries

Added pinned Playwright1.65 development dependency and a real Chromium/Vite/
FastAPI/PostgreSQL synthetic journey. Servers/sessions are owned and cleaned;
remote browser origins are rejected. Models remain mocked, SQL/auth/graphs/
checkpoints/tools/approvals/worker transactions are real. CI opts into Chromium;
ordinary backend runs skip it unless RUN_BROWSER_E2E=1.

First run caught approval datetime values failing JSONB serialization in persisted
conversation results. Added JSON-safe conversion and a direct multi-turn test.
The next failure was a collapsed-details locator; fixed the interaction rather
than changing app behavior. Journey subsequently passed, including foreign-ID404,
manual two-step approval/execution, mobile width, logout and0page errors.

Fixed lexical dataset:2identifier queries against3chunks, Recall@3/MRR1.0,
citation contract2/2 and no-match abstention1/1. These small fixture results are
not semantic model quality; mocked faithfulness1.0 is never reported as accuracy.
Fault matrix and limitations are explicit in VERIFICATION.md.

## Interview questions

1. What did E2E find beyond unit tests? Datetime serialization across approval/history.
2. Why real DB? Transactions, JSONB, tenant predicates and checkpoint races matter.
3. What is mocked? Model generation/embeddings/reranker/evaluator, not auth or writes.
4. Why separate sessions? Request/worker/checkpointer threads must not share one.
5. Does perfect tiny recall prove quality? No; identifier fixtures test ranking contracts.
6. Why explicit browser opt-in? Chromium/system dependencies are heavier than unit tests.
7. How recover failures? Deterministic regression first, fix cause, repeat the journey.

Follow-up fixed disconnected live aggregates: independent privacy-safe request
metric writes and tenant/request-correlated worker faithfulness completion.
New additive migration1a29a0000001 represents unknown usage/cost as null without
rewriting applied history or inventing values. Tests protect unrelated request
work on write failure and foreign-tenant score joins.20metric writes measured
p50 3.736ms/p95 4.770ms. With real values the browser exposed mobile overflow;
number formatting, bounded grid children and a scrollable quality table fixed it.
Initial verification command used a wrong working directory and lacked sandbox
DB access; corrected. An early hook patch landed at claim instead of completion,
causing NameError; targeted tests caught it and the hook was moved before passing.
Latest metric/migration/browser targets passed; final full suite follows.

Final full suite with browser enabled:212passed in46.30s, no failures/skips.
17frontend tests/build passed; secret scan0; npm audit0known. Applied migrations
only in disposable test DBs. Live Slack/cloud/model quality remain pending.
