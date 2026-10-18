from sqlalchemy.orm import Session

from app.services.retrieval_service import retrieve_chunks
from app.services.keyword_retrieval_service import keyword_search


def reciprocal_rank_fusion(
    dense_results: list[dict],
    keyword_results: list[dict],
    k: int = 60,
) -> list[dict]:

    combined = {}

    for results in (dense_results, keyword_results):

        for rank, chunk in enumerate(results, start=1):

            chunk_id = chunk["chunk_id"]

            if chunk_id not in combined:
                combined[chunk_id] = {
                    **chunk,
                    "rrf_score": 0.0,
                }

            combined[chunk_id]["rrf_score"] += (
                1.0 / (k + rank)
            )

    return sorted(
        combined.values(),
        key=lambda x: (
            -x["rrf_score"],
            x["chunk_id"],
        ),
    )


def hybrid_retrieve(
    db: Session,
    query: str,
    customer_id: int,
    top_k: int = 5,
    candidate_k: int = 20,
) -> list[dict]:

    candidate_k = max(candidate_k, top_k)

    dense_results = retrieve_chunks(
        db=db,
        query=query,
        customer_id=customer_id,
        top_k=candidate_k,
    )

    keyword_results = keyword_search(
        db=db,
        query=query,
        customer_id=customer_id,
        top_k=candidate_k,
    )

    fused = reciprocal_rank_fusion(
        dense_results,
        keyword_results,
    )

    return fused[:top_k]