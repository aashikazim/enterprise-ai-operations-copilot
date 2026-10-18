from functools import lru_cache
from sentence_transformers import CrossEncoder


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def get_reranker():
    return CrossEncoder(MODEL_NAME)


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 5,
) -> list[dict]:

    if not chunks:
        return []

    model = get_reranker()

    pairs = [
        (query, chunk["content"])
        for chunk in chunks
    ]

    scores = model.predict(pairs)

    reranked = []

    for chunk, score in zip(chunks, scores):
        reranked.append({
            **chunk,
            "rerank_score": float(score),
        })

    reranked.sort(
        key=lambda x: (
            -x["rerank_score"],
            x["chunk_id"],
        )
    )

    return reranked[:top_k]