from app.services.hybrid_retrieval_service import (
    hybrid_retrieve,
    reciprocal_rank_fusion,
)
from unittest.mock import patch

import pytest


def test_rrf_combines_overlapping_results():

    dense = [
        {"chunk_id": 1, "content": "A"},
        {"chunk_id": 2, "content": "B"},
        {"chunk_id": 3, "content": "C"},
    ]

    keyword = [
        {"chunk_id": 2, "content": "B"},
        {"chunk_id": 1, "content": "A"},
        {"chunk_id": 4, "content": "D"},
    ]

    results = reciprocal_rank_fusion(
        dense,
        keyword,
    )

    assert len(results) == 4

    assert results[0]["chunk_id"] == 1
    assert results[1]["chunk_id"] == 2

    assert results[0]["rrf_score"] > 0


def test_rrf_handles_empty_results():

    results = reciprocal_rank_fusion([], [])

    assert results == []


def test_rrf_handles_one_retriever():

    dense = [
        {"chunk_id": 10, "content": "First"},
        {"chunk_id": 20, "content": "Second"},
    ]

    results = reciprocal_rank_fusion(dense, [])

    assert [r["chunk_id"] for r in results] == [10, 20]


@pytest.mark.parametrize("top_k,candidate_k", [(2, 5), (5, 2)])
def test_hybrid_uses_bm25_with_tenant_and_candidate_limit(top_k, candidate_k):
    db = object()
    dense = [{"chunk_id": 2}, {"chunk_id": 1}]
    lexical = [{"chunk_id": 1}, {"chunk_id": 3}]
    with (
        patch("app.services.hybrid_retrieval_service.retrieve_chunks", return_value=dense) as dense_search,
        patch("app.services.hybrid_retrieval_service.bm25_search", return_value=lexical) as bm25,
    ):
        result = hybrid_retrieve(db, "ERR_AUTH_403", 17, top_k, candidate_k)
    for search in (dense_search, bm25):
        search.assert_called_once_with(
            db=db, query="ERR_AUTH_403", customer_id=17, top_k=max(top_k, candidate_k)
        )
    assert result == reciprocal_rank_fusion(dense, lexical)[:top_k]
    assert result[0]["chunk_id"] == 1


def test_rrf_exact_scores_and_deterministic_ties():
    dense = [{"chunk_id": 20}, {"chunk_id": 10}]
    lexical = [{"chunk_id": 10}, {"chunk_id": 20}]
    expected = 1 / 61 + 1 / 62
    for _ in range(3):
        for first, second in ((dense, lexical), (lexical, dense)):
            result = reciprocal_rank_fusion(first, second)
            assert [item["chunk_id"] for item in result] == [10, 20]
            assert [item["rrf_score"] for item in result] == pytest.approx([expected, expected])
