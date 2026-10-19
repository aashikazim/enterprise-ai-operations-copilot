
import pytest

from app.services.faithfulness_service import (
    ClaimAssessment,
    FaithfulnessAssessment,
    calculate_faithfulness,
)
from app.services.faithfulness_service import format_evidence


def test_evidence_uses_source_ids_not_document_ids():
    chunks = [
        {
            "document_id": 2,
            "title": "Password Security Policy",
            "content": "Employees must never share passwords.",
        }
    ]

    evidence = format_evidence(chunks)

    assert "[Source 1]" in evidence
    assert "Document ID: 2" not in evidence
    assert "Employees must never share passwords." in evidence

def test_all_claims_supported():
    assessment = FaithfulnessAssessment(
        claims=[
            ClaimAssessment(
                claim="Contact IT.",
                cited_source_ids=[1],
                verdict="supported",
                explanation="Source 1 explicitly states this.",
            ),
            ClaimAssessment(
                claim="Verify identity.",
                cited_source_ids=[1],
                verdict="supported",
                explanation="Source 1 explicitly states this.",
            ),
        ]
    )

    result = calculate_faithfulness(assessment)

    assert result["faithfulness_score"] == 1.0
    assert result["supported_claims"] == 2


def test_partially_supported():
    assessment = FaithfulnessAssessment(
        claims=[
            ClaimAssessment(
                claim="Contact IT.",
                cited_source_ids=[1],
                verdict="supported",
                explanation="Supported.",
            ),
            ClaimAssessment(
                claim="Recovery takes 10 minutes.",
                cited_source_ids=[],
                verdict="unsupported",
                explanation="No time guarantee exists.",
            ),
        ]
    )

    result = calculate_faithfulness(assessment)

    assert result["faithfulness_score"] == 0.5
    assert result["unsupported_claims"] == 1


def test_no_claims():
    assessment = FaithfulnessAssessment(claims=[])

    result = calculate_faithfulness(assessment)

    assert result["faithfulness_score"] is None
    assert result["total_claims"] == 0
