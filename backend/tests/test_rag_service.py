
from unittest.mock import patch

from app.services.rag_service import answer_question


def test_rag_returns_answer_and_sources():
    mock_chunks = [
        {
            "chunk_id": 1,
            "document_id": 10,
            "title": "Employee Password Recovery Policy",
            "chunk_index": 0,
            "content": (
                "Employees who cannot use MFA must contact "
                "the IT help desk for identity verification."
            ),
            "similarity": 0.91,
            "rrf_score": 0.032,
            "rerank_score": 6.5,
        }
    ]

    with (
        patch(
            "app.services.rag_service.retrieve_rag_context",
            return_value=mock_chunks,
        ) as mock_retrieve,
        patch(
            "app.services.rag_service.generate_answer",
            return_value=(
                "Contact the IT help desk for identity verification."
            ),
        ) as mock_generate,
    ):
        result = answer_question(
            db=None,
            question="What if I cannot use MFA?",
            customer_id=1,
            top_k=5,
        )

    assert result["answer"] == (
        "Contact the IT help desk for identity verification."
    )

    assert len(result["sources"]) == 1
    assert result["sources"][0]["document_id"] == 10

    mock_retrieve.assert_called_once_with(
        db=None,
        question="What if I cannot use MFA?",
        customer_id=1,
        top_k=5,
    )

    mock_generate.assert_called_once()


def test_rag_returns_fallback_when_no_chunks():
    with (
        patch(
            "app.services.rag_service.retrieve_rag_context",
            return_value=[],
        ),
        patch(
            "app.services.rag_service.generate_answer",
        ) as mock_generate,
    ):
        result = answer_question(
            db=None,
            question="What is the vacation policy?",
            customer_id=1,
            top_k=5,
        )

    assert result["sources"] == []
    assert "could not find" in result["answer"].lower()

    mock_generate.assert_not_called()
