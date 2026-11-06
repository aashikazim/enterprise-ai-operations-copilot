# Day 26 — Measure before caching

The active BM25 path rebuilt tokens, frequencies and index on every search.
Added an opt-in eight-entry LRU of computational indexes with tenant/content
keys and a 250k-character corpus ceiling. Fresh tenant-filtered SQL still runs;
results never come from a cached authorization decision. Dense ties now order
by chunk ID. No dependency, migration or Redis service was necessary.

Measured the same 200-chunk corpus and query before/after: p50 6.964/4.415ms,
p95 8.137/5.410ms over 30 warm requests. Queue and role benchmarks were rerun;
see PERFORMANCE.md for exact values and limitations. No paid model was called.
Tests cover cross-tenant identical corpora, edits/deletions and equivalent ranks.
A timing assertion would be flaky, so only correctness gates the test.

## Interview questions

1. Why cache an index? Tokenization and frequency construction repeated per call.
2. Why reload SQL? Authorization and corpus freshness must not be cached blindly.
3. What invalidates entries? Exact ordered contents and tenant form the key.
4. Why default off? Raw text remains in memory until eviction/restart.
5. Does the benchmark prove RAG latency? No; embeddings, reranking and LLM are separate.
6. Why avoid Redis? A bounded local computation cache solves the measured requirement.
7. What follows? Sustained HTTP and real-model measurements require separate workloads.
