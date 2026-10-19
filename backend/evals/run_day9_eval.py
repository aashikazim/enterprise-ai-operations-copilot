
import json
import os
from pathlib import Path

from openai import OpenAI

from app.services.faithfulness_service import (
    evaluate_faithfulness,
)


def main():
    path = Path(__file__).with_name("day9_cases.json")
    cases = json.loads(path.read_text(encoding="utf-8"))

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    results = []

    for case in cases:
        result = evaluate_faithfulness(
            question=case["question"],
            answer=case["answer"],
            chunks=case["chunks"],
            client=client,
            model=model,
        )

        actual = result["faithfulness_score"]
        expected = case["expected_faithfulness"]

        results.append({
            "id": case["id"],
            "expected": expected,
            "actual": actual,
            "absolute_error": (
                abs(actual - expected)
                if actual is not None
                else None
            ),
            "claims": result["claims"],
        })

    output_path = Path(__file__).with_name(
        "day9_results.json"
    )

    output_path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    for result in results:
        print(
            f"{result['id']}: "
            f"expected={result['expected']}, "
            f"actual={result['actual']}"
        )

    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
