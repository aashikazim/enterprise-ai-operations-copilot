# API examples

Use Swagger at http://127.0.0.1:8000/docs for interactive authorized calls. All
examples below are JSON bodies, not embedded credentials. Login uses URL-encoded
username/password at POST/auth/login; keep the returned JWT only in local memory.
Never paste JWTs into docs, URLs, screenshots, committed files or chat.

## Grounded question

POST/rag/ask with Authorization: Bearer <your locally held token>:

```json
{"question":"What does the synthetic MFA recovery policy require?","top_k":5}
```

Response includes answer, source_id/document_id/title/chunk_index/similarity,
abstained and citation_validation. Source preview is a separate GET
/knowledge/documents/{document_id}/chunks/{chunk_index}; it rechecks current tenant.

## Conversation

1. POST/conversations with no body creates an owner-scoped ID.
2. POST/conversations/{id}/messages with `{"question":"list tickets","top_k":5}`.
3. GET/conversations/{id} returns bounded paginated messages/results.
4. After an interrupted run, inspect state, then POST/conversations/{id}/resume
   explicitly. A completed run cannot be resumed as an automatic retry.
5. DELETE/conversations/{id} removes idle owner data; active leases return409.

## Proposed ticket status change

POST/agents/run with `{"question":"close ticket 1"}` creates a proposal only.
Replace1with an authorized synthetic ticket ID. Alternatively POST/approvals:

```json
{"ticket_id":1,"status":"closed","idempotency_key":"864121ea-9dbf-42fc-9f2d-1e910367ce78"}
```

Use a fresh UUID per intended proposal; reuse it only to retry the same proposal.
An admin calls POST/approvals/{id}/approve, then separately
POST/approvals/{id}/execute. Rejection is POST/approvals/{id}/reject. No request
body is required for those transitions. Approval expires; server verifies role,
tenant, digest, original target state and prior decision at execution.

## Monitoring

GET/rag/monitoring/summary?hours=24 is tenant-admin-only; jobs accepts bounded
limit/offset and status. GET/rag/evaluations/{id} is tenant-scoped. Unknown token
usage/cost and unavailable faithfulness stay null. RAG core latency excludes
metric/enqueue writes. Do not interpret an empty quality table as measured zero
error or zero model cost.
