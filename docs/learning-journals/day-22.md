# Day22 — conversation and grounded-answer UI

Date:2026-11-05. Add typed conversation/agent/RAG contracts, conversation list,
new thread/message composer, explicit agent/knowledge modes, safe steps/results,
source-number buttons and authorized chunk previews. React renders plain text;
no raw HTML. Source preview API filters both document and chunk tenant. Old
saved results missing newer arrays remain readable. No streaming is invented.

Abort stops browser waiting only; server generation may finish. UI warns before
manual retry and exposes explicit interrupted-run resume. Source preview requests
are aborted on context changes to avoid stale source-to-answer mapping.
8frontend tests/build passed. Source authorization target1passed in0.38s;
backend full regression in implementation status. Tests cover modes, citations,
source preview, abstention, safe failure/no auto retry. No dependencies/migration.
One initial build command used repo root instead of frontend; corrected command
is npm --prefix frontend run build. Paid calls mocked; visual QA remains separate.

## FDE interview questions

1. **Why distinguish modes?** Direct knowledge requests and stateful operations
have different persistence/tool behavior; users need an explicit choice.
2. **Does citation validity imply support?** No. UI distinguishes source numbers
from actual evidence, and invites source inspection.
3. **Why authorize previews separately?** An opaque source ID in a response is
not permission to retrieve its document after tenant/permission changes.
4. **Does cancel stop a model?** No. It aborts this HTTP wait; server work may
continue, so automatic retry could duplicate cost.
5. **Why avoid streaming now?** The backend has no safe streaming contract;
use honest request progress rather than a fake token stream.
6. **How avoid source confusion?** Preserve ordered source metadata and cancel
stale preview requests when selecting another conversation/source.
