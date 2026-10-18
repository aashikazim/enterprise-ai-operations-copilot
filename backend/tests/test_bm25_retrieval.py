
from rank_bm25 import BM25Okapi

from app.services.bm25_retrieval_service import tokenize


def test_tokenization_preserves_error_codes():
    tokens = tokenize("Fix ERR_AUTH_403 in the API")

    assert "err_auth_403" in tokens
    assert "api" in tokens


def test_bm25_ranks_relevant_chunk_first():
    documents = [
        "Employee vacation and travel reimbursement",
        "Authentication failure ERR_AUTH_403 requires admin review",
        "Database backup and storage retention",
        "Password reset and MFA recovery procedures",
    ]

    corpus = [tokenize(doc) for doc in documents]
    bm25 = BM25Okapi(corpus)

    scores = bm25.get_scores(
        tokenize("ERR_AUTH_403 authentication failure")
    )

    best_index = int(scores.argmax())

    assert best_index == 1
