def recall_at_k(
    retrieved_ids: list[int],
    relevant_ids: set[int],
    k: int,
) -> float:
    if not relevant_ids:
        return 0.0

    retrieved = set(retrieved_ids[:k])

    return len(
        retrieved.intersection(relevant_ids)
    ) / len(relevant_ids)


def reciprocal_rank(
    retrieved_ids: list[int],
    relevant_ids: set[int],
) -> float:
    for rank, document_id in enumerate(
        retrieved_ids, start=1
    ):
        if document_id in relevant_ids:
            return 1.0 / rank

    return 0.0


def mean_reciprocal_rank(
    queries: list[dict],
) -> float:
    if not queries:
        return 0.0

    scores = [
        reciprocal_rank(
            item["retrieved_ids"],
            set(item["relevant_ids"]),
        )
        for item in queries
    ]

    return sum(scores) / len(scores)