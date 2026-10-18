
import json
import os
import time
from pathlib import Path

import httpx

from app.evals.answer_quality import (
    abstention_correct,
    keyword_coverage,
)


BASE_URL = os.getenv(
    "EVAL_BASE_URL",
    "http://localhost:8000",
)

TOKEN = os.getenv("EVAL_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "Set EVAL_TOKEN to a valid JWT access token."
    )

cases_path = (
    Path(__file__).parent / "day8_cases.json"
)

cases = json.loads(
    cases_path.read_text(encoding="utf-8")
)

results = []

with httpx.Client(timeout=120.0) as client:
    for case in cases:
        started = time.perf_counter()

        response = client.post(
            f"{BASE_URL}/rag/ask",
            headers={
                "Authorization": f"Bearer {TOKEN}"
            },
            json={
                "question": case["question"],
                "top_k": 5,
            },
        )

        response.raise_for_status()

        latency_ms = (
            time.perf_counter() - started
        ) * 1000

        result = response.json()
        print("DEBUG API RESPONSE:", json.dumps(result, indent=2))

        coverage = keyword_coverage(
            result["answer"],
            case["expected_keywords"],
        )

        abstention_ok = abstention_correct(
            result["abstained"],
            case["should_abstain"],
        )

        citation_check = result[
            "citation_validation"
        ]

        results.append({
            "id": case["id"],
            "keyword_coverage": coverage,
            "abstention_correct": abstention_ok,
            "citations_valid": citation_check[
                "citations_valid"
            ],
            "has_citations": citation_check[
                "has_citations"
            ],
            "latency_ms": round(latency_ms, 2),
        })

for result in results:
    print(json.dumps(result, indent=2))

if results:
    print(
        "Abstention accuracy:",
        sum(
            r["abstention_correct"]
            for r in results
        ) / len(results),
    )

    print(
        "Average latency (ms):",
        round(
            sum(r["latency_ms"] for r in results)
            / len(results),
            2,
        ),
    )
