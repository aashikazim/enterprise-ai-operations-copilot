import pytest

from app.evals.retrieval_metrics import (
    recall_at_k,
    reciprocal_rank,
    mean_reciprocal_rank,
)


def test_recall_at_k():
    result = recall_at_k(
        retrieved_ids=[10, 20, 30, 40, 50],
        relevant_ids={20, 40},
        k=3,
    )

    assert result == 0.5


def test_reciprocal_rank():
    result = reciprocal_rank(
        retrieved_ids=[10, 20, 30],
        relevant_ids={20},
    )

    assert result == 0.5


def test_mean_reciprocal_rank():
    queries = [
        {
            "retrieved_ids": [10, 20],
            "relevant_ids": [10],
        },
        {
            "retrieved_ids": [30, 40],
            "relevant_ids": [40],
        },
    ]

    assert mean_reciprocal_rank(queries) == 0.75


def test_no_relevant_documents():
    assert recall_at_k([1, 2], set(), 2) == 0.0
    assert reciprocal_rank([1, 2], {3}) == 0.0