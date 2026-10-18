from sqlalchemy import text
from sqlalchemy.orm import Session


def keyword_search(
    db: Session,
    query: str,
    customer_id: int,
    top_k: int = 10,
) -> list[dict]:

    sql = text("""
        SELECT
            dc.id AS chunk_id,
            dc.document_id,
            d.title,
            dc.chunk_index,
            dc.content,
            ts_rank_cd(
                to_tsvector('english', dc.content),
                websearch_to_tsquery('english', :query)
            ) AS keyword_score

        FROM document_chunks dc

        JOIN documents d
            ON d.id = dc.document_id

        WHERE
            dc.customer_id = :customer_id
            AND d.customer_id = :customer_id
            AND to_tsvector('english', dc.content)
                @@ websearch_to_tsquery('english', :query)

        ORDER BY keyword_score DESC, dc.id ASC
        LIMIT :top_k
    """)

    rows = db.execute(
        sql,
        {
            "query": query,
            "customer_id": customer_id,
            "top_k": top_k,
        },
    ).mappings().all()

    return [
        {
            "chunk_id": row["chunk_id"],
            "document_id": row["document_id"],
            "title": row["title"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "keyword_score": float(row["keyword_score"]),
        }
        for row in rows
    ]