
from openai import OpenAI

from app.services.faithfulness_service import (
    evaluate_faithfulness,
)


def audit_rag_answer(
    question: str,
    answer: str,
    chunks: list[dict],
    api_key: str,
    model: str = "gpt-4.1-mini",
) -> dict:
    client = OpenAI(api_key=api_key)

    return evaluate_faithfulness(
        question=question,
        answer=answer,
        chunks=chunks,
        client=client,
        model=model,
    )
