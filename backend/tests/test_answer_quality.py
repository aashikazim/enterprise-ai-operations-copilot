from app.evals.answer_quality import (
    extract_citations,
    validate_citations,
    keyword_coverage,
    abstention_correct,
)


def test_extract_citations():
    answer = (
        "Reset your password [Source 1]. "
        "Contact IT [Source 2]. "
        "See [Source 1] again."
    )

    assert extract_citations(answer) == [1, 2]


def test_valid_citations():
    result = validate_citations(
        "Follow the policy [Source 1].",
        {1, 2},
    )

    assert result["citations_valid"] is True
    assert result["invalid_source_ids"] == []


def test_invalid_citations():
    result = validate_citations(
        "Follow the policy [Source 99].",
        {1, 2},
    )

    assert result["citations_valid"] is False
    assert result["invalid_source_ids"] == [99]


def test_keyword_coverage():
    answer = (
        "Contact the IT help desk for "
        "password recovery."
    )

    score = keyword_coverage(
        answer,
        ["help desk", "password"],
    )

    assert score == 1.0


def test_abstention_correctness():
    assert abstention_correct(True, True)
    assert not abstention_correct(False, True)