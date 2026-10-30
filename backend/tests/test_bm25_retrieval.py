
from rank_bm25 import BM25Okapi

from app.services.bm25_retrieval_service import tokenize
from app.services.bm25_retrieval_service import bm25_search
from app.db.models import Document, DocumentChunk
import pytest


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


def seed_chunks(db, customer_id, contents):
    document = Document(title="Synthetic retrieval policy", content="Synthetic data", customer_id=customer_id)
    db.add(document)
    db.flush()
    chunks = [
        DocumentChunk(
            document_id=document.id, customer_id=customer_id,
            chunk_index=index, content=content, embedding=[1.0] + [0.0] * 383,
        )
        for index, content in enumerate(contents)
    ]
    db.add_all(chunks)
    db.commit()
    return chunks


@pytest.mark.parametrize("contents", [["MFA"], ["MFA", "travel"], ["MFA", "MFA"]])
def test_bm25_preserves_small_corpus_matches(db, test_customer, contents):
    chunks = seed_chunks(db, test_customer.id, contents)
    result = bm25_search(db, "MFA", test_customer.id)
    expected = [chunk.id for chunk in chunks if chunk.content == "MFA"]
    assert [item["chunk_id"] for item in result] == expected
    assert all(item["bm25_score"] > 0 for item in result)


@pytest.mark.parametrize("query,top_k", [("missing", 5), ("!!!", 5), ("MFA", 0), ("MFA", -1)])
def test_bm25_no_matches_or_invalid_search(db, test_customer, query, top_k):
    seed_chunks(db, test_customer.id, ["MFA"])
    assert bm25_search(db, query, test_customer.id, top_k) == []


@pytest.mark.parametrize("contents", [[], ["!!!", "   "]])
def test_bm25_empty_corpus(db, test_customer, contents):
    seed_chunks(db, test_customer.id, contents)
    assert bm25_search(db, "MFA", test_customer.id) == []


def test_bm25_ranks_identifiers_and_limits_results(db, test_customer):
    chunks = seed_chunks(db, test_customer.id, [
        "MFA recovery", "ERR_AUTH_403 authentication failure", "travel reimbursement", "backup storage",
    ])
    result = bm25_search(db, "ERR_AUTH_403 authentication", test_customer.id, top_k=1)
    assert [item["chunk_id"] for item in result] == [chunks[1].id]
