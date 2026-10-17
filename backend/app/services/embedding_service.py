from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def get_embedding_model():
    return SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()

    vector = model.encode(
        text,
        normalize_embeddings=True,
    )

    return vector.tolist()