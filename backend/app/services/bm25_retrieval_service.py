
import re

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk



def tokenize(text: str) -> list[str]:
    """Normalize text while preserving identifiers such as ERR_AUTH_403."""
    return re.findall(r"[a-z0-9_]+", text.lower())


def bm25_search(
    db: Session,
    query: str,
    customer_id: int,
    top_k: int = 10,
) -> list[dict]:
    """
    Perform true Okapi BM25 ranking over the tenant's document chunks.

    Day 7 implementation:
    - Load only chunks belonging to the authenticated tenant.
    - Build an in-memory BM25 index.
    - Score and rank chunks.
    """

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

    if not rows or top_k <= 0:
        return []

    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    tokenized_corpus = [
        tokenize(chunk.content)
        for chunk, _ in rows
    ]

    if not any(tokenized_corpus):
        return []

    bm25 = BM25Okapi(tokenized_corpus)

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
