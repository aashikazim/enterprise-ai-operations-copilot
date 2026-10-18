from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.services.embedding_service import embed_text


def retrieve_chunks(
    db: Session,
    query: str,
    customer_id: int,
    top_k: int = 5,
) -> list[dict]:

    query_vector = embed_text(query)

    distance = DocumentChunk.embedding.cosine_distance(
        query_vector
    )

    statement = (
        select(
            DocumentChunk,
            Document.title,
            distance.label("distance"),
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .where(
            DocumentChunk.customer_id == customer_id,
            Document.customer_id == customer_id,
        )
        .order_by(distance)
        .limit(top_k)
    )

    rows = db.execute(statement).all()

    return [
        {
            "document_id": chunk.document_id,
            "title": title,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "similarity": round(
                max(0.0, min(1.0, 1.0 - float(dist))),
                4,
            ),
        }
        for chunk, title, dist in rows
    ]