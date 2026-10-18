from unittest.mock import patch

from app.services.rag_service import answer_question


def test_rag_answer_with_sources():
    fake_chunks = [
        {
            "document_id": 7,
            "title": "Password Policy",
            "chunk_index": 0,
            "content": "Use the password reset portal.",
            "similarity": 0.91,
        }
    ]

    with (
        patch(
            "app.services.rag_service.retrieve_chunks",
            return_value=fake_chunks,
        ),
        patch(
            "app.services.rag_service.generate_answer",
            return_value="Use the password reset portal.",
        ),
    ):
        result = answer_question(
            db=None,
            question="How do I reset my password?",
            customer_id=1,
        )

    assert result["answer"] == (
        "Use the password reset portal."
    )

    assert len(result["sources"]) == 1
    assert result["sources"][0]["document_id"] == 7


def test_rag_no_documents():
    with patch(
        "app.services.rag_service.retrieve_chunks",
        return_value=[],
    ):
        result = answer_question(
            db=None,
            question="What is our policy?",
            customer_id=1,
        )

    assert result["sources"] == []
    assert "could not find" in result["answer"].lower()