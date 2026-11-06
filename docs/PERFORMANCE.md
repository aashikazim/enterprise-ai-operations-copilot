# Reproducible local performance assessment

Run serially from `backend/` after preparing the two disposable databases:

```sh
.venv/bin/python -m pytest tests/test_retrieval_performance.py tests/test_queue_scaling.py tests/test_coordination_assessment.py -q -s -p no:cacheprovider
```

These tests use real PostgreSQL, synthetic records and mocked evaluators. They
reset only the guarded test database; never run with development data. Each
measurement is a single local run, without production concurrency or live model
latency. Correctness assertions are stable; timing is reported, not asserted.

## Day 26 measurements (2026-11-05)

| Workload | p50 | p95 | Other measured result |
|---|---:|---:|---|
| BM25 uncached, 200 chunks, 30 warm searches | 6.964 ms | 8.137 ms | Recall@5=1, MRR=1, errors=0 |
| Same data/query, bounded warm index cache | 4.415 ms | 5.410 ms | Identical results |
| One queue worker, 40 synthetic jobs | — | 370 ms queue wait | 100.77 jobs/s |
| Four queue workers, same workload | — | 136 ms queue wait | 265.44 jobs/s |
| Single-role read workflow, 50 cases | 3.701 ms | 7.780 ms | 50/50 expected results |
| Three-role candidate, same cases | 3.854 ms | 6.737 ms | 50/50 expected results |

Warm BM25 p50 decreased 36.6% in this run. This measures SQL row loading,
tokenization/index building and ranking, including identical per-request tenant
filters. It is not an end-to-end RAG speedup. The repeated identifier query is
intentionally narrow; its perfect recall does not establish semantic quality.

`RAG_BM25_CACHE_ENABLED=false` remains the default. When enabled, eight LRU entries
retain at most 250,000 characters per corpus plus token/index overhead. Keys
include tenant and exact ordered contents; every request still loads authorized
rows and fresh result metadata. Edits/deletes invalidate the key. Old content
can remain in process memory until eviction or restart; this option may conflict
with strict immediate-erasure policies. Oversized corpora bypass the cache.
Disable it and restart processes to clear retained content. No Redis was added.

Existing request/evaluation tests mock paid providers. Live token usage, cost,
faithfulness, model throughput, sustained concurrent HTTP load and end-to-end RAG
p50/p95 have not been measured; do not infer them from these microbenchmarks.

A second targeted run measured authenticated TestClient orchestration (30 calls,
real JWT/user lookup, mocked RAG/model service): `/rag/ask` p50 3.725ms,
p95 8.094ms; `/agents/run` p50 10.269ms, p95 15.076ms; both zero HTTP errors.
These exclude socket/TLS and model/retrieval execution. Repeated BM25 p50 was
7.643/4.540ms and p95 8.301/5.830ms, showing expected local timing variation.
