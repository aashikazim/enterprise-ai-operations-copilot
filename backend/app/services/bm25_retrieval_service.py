
import re
from collections import Counter
from math import log1p
from functools import lru_cache

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.db.database import get_settings



def tokenize(text: str) -> list[str]:
    """Normalize text while preserving identifiers such as ERR_AUTH_403."""
    return re.findall(r"[a-z0-9_]+", text.lower())


def _build_index(customer_id: int, corpus: tuple[str, ...]):
    tokens = [tokenize(content) for content in corpus]
    if not any(tokens):
        return None
    index = BM25Okapi(tokens)
    frequencies = Counter(token for row in tokens for token in set(row))
    index.idf = {
        token: log1p((len(corpus) - count + 0.5) / (count + 0.5))
        for token, count in frequencies.items()
    }
    return index


# Default-off: retains raw corpus text in process memory until eviction/restart.
# Exact content keys invalidate edits/deletions; tenant identity prevents sharing.
# Eight entries, each capped at 250k characters. DB authorization is never cached.
_cached_index = lru_cache(maxsize=8)(_build_index)


def bm25_search(
    db: Session,
    query: str,
    customer_id: int,
    top_k: int = 10,
) -> list[dict]:
    """
    Perform true Okapi BM25 ranking over the tenant's document chunks.

    - Load only chunks belonging to the authenticated tenant.
    - Build an in-memory BM25 index.
    - Score and rank chunks.
    - Use positive Robertson IDF: log(1 + (N - df + .5)/(df + .5)).
      The library's raw IDF can be zero/negative for small corpora;
      positive IDF preserves matching singleton and common-term results.
    """

    query_tokens = tokenize(query)
    if top_k <= 0 or not query_tokens:
        return []

    stmt = (
        select(DocumentChunk, Document.title)
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .where(
            DocumentChunk.customer_id == customer_id,
            Document.customer_id == customer_id,
        )
        .order_by(DocumentChunk.id)
    )

    rows = db.execute(stmt).all()

    if not rows:
        return []

    corpus = tuple(chunk.content for chunk, _ in rows)
    use_cache = get_settings().rag_bm25_cache_enabled and sum(map(len, corpus)) <= 250_000
    build = _cached_index if use_cache else _build_index
    bm25 = build(customer_id, corpus)
    if bm25 is None:
        return []

    scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(
        range(len(rows)),
        key=lambda i: (-float(scores[i]), rows[i][0].id),
    )

    results = []

    for i in ranked_indices:
        score = float(scores[i])

        if score <= 0:
            continue

        chunk, title = rows[i]

        results.append({
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "title": title,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "bm25_score": score,
        })

        if len(results) >= top_k:
            break

    return results
