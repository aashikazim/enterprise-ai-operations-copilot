from app.services.hybrid_retrieval_service import (
    reciprocal_rank_fusion,
)


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