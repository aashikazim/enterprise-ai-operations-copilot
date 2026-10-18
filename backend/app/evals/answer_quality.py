
import re


CITATION_PATTERN = re.compile(
    r"\[Source\s+(\d+)\]",
    flags=re.IGNORECASE,
)


def extract_citations(answer: str) -> list[int]:
    """Extract distinct cited source IDs in first-use order."""
    return list(
        dict.fromkeys(
            int(value)
            for value in CITATION_PATTERN.findall(answer)
        )
    )


def validate_citations(
    answer: str,
    available_source_ids: set[int],
) -> dict:
    cited_ids = extract_citations(answer)

    invalid_ids = [
        source_id
        for source_id in cited_ids
        if source_id not in available_source_ids
    ]

    return {
        "cited_source_ids": cited_ids,
        "invalid_source_ids": invalid_ids,
        "citations_valid": len(invalid_ids) == 0,
        "has_citations": len(cited_ids) > 0,
    }

def keyword_coverage(
    answer: str,
    expected_keywords: list[str],
) -> float:
    if not expected_keywords:
        return 1.0

    normalized_answer = answer.lower()

    matched = sum(
        keyword.lower() in normalized_answer
        for keyword in expected_keywords
    )

    return matched / len(expected_keywords)


def abstention_correct(
    actual_abstained: bool,
    expected_abstained: bool,
) -> bool:
    return actual_abstained == expected_abstained
