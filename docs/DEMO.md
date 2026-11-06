# Seven-minute engineering demo

Use only synthetic local records. No publishing, external writes or paid model
execution occurs automatically. Browser automation screenshots use disposable
fixtures; their generated answer/evaluator are mocked and labeled as such.

## Prepare

1. Follow README/DEPLOYMENT.md with independent local secrets and loopback ports.
2. Run `python -m scripts.seed_demo --confirm-local-demo` inside the backend
   container (full Compose command in README), choose a 12+ character password and
   record the two printed ticket IDs. No default deployed password is supplied.
3. Sign in as admin@demo.example. The seed refuses duplicate records; it never
   deletes/resets data. It creates tickets/accounts, not fake embeddings.
4. To demonstrate actual generation, separately configure an approved provider
   and model downloads, then upload the text in backend/evals/demo_documents.json.
   This live step may incur cost and was not executed during this implementation.
5. For a fully offline repeatable journey, run the opt-in Chromium integration
   from VERIFICATION.md. It supplies deterministic model seams in test process
   memory only; no mock mode or fake model switch is shipped in production API.

## Walkthrough

| Time | Show | Engineering point |
|---|---|---|
| 0:00–0:45 | Problem, overview, architecture | Tenant evidence and accountable actions |
| 0:45–1:30 | Login, Administration, synthetic records | JWT resolves tenant; no unchecked identity field |
| 1:30–2:30 | Knowledge question and source preview | Dense+BM25/RRF/reranker, numbered citations; inspect evidence |
| 2:30–3:15 | Conversation: `list tickets`, `show ticket N` | Typed read tools, bounded graph and persisted history |
| 3:15–4:30 | `close ticket N`, Actions & history | Requested proposal leaves ticket unchanged; approve then separately execute |
| 4:30–5:15 | Other tenant ticket probe and execution replay |404/authorization and idempotent atomic mutation |
| 5:15–6:00 | Quality/queue dashboard and worker | Opt-in durable sampled evaluation; no inline evaluator |
| 6:00–7:00 | Tests, performance evidence, tradeoffs and limits | Local verified, live Slack/AWS pending, no invented model quality |

If no provider is configured, demonstrate records/tools/approval interactively
and show the automated browser journey for grounded-answer fixtures. State the
mocking boundary aloud. Empty metrics/Not measured are valid states, not failed
measurements. Sampling remains off until an owner enables it with cost/data
approval. Do not fabricate a live job or real provider score for the demo.

## Reproduce screenshots

Install frontend dependencies/browser. From backend on the verified Linux host:

```sh
RUN_BROWSER_E2E=1 BROWSER_EXECUTABLE_PATH=/usr/bin/google-chrome E2E_SCREENSHOT_DIR="$PWD/../docs/screenshots" .venv/bin/python -m pytest tests/test_browser_journey.py -q -s -p no:cacheprovider
```

Screenshots capture only synthetic disposable data, not browser tokens, provider
keys or customer documents. No video recording/publishing is claimed.
