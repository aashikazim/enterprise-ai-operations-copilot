
import os
from pathlib import Path
from dotenv import load_dotenv


from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.jobs.evaluation_queue import (
    enqueue_evaluation,
)

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

def main():
    engine = create_engine(
        os.environ["DATABASE_URL"]
    )

    customer_id = int(
        os.environ["DEMO_CUSTOMER_ID"]
    )

    evidence = [
        {
            "document_id": 1,
            "title": "MFA Recovery Policy",
            "content": (
                "Employees who cannot access MFA "
                "must contact the IT help desk "
                "for identity verification."
            ),
        }
    ]

    with Session(engine) as db:
        job = enqueue_evaluation(
            db=db,
            customer_id=customer_id,
            question="What if MFA is unavailable?",
            answer=(
                "Employees must contact IT for "
                "identity verification [Source 1]."
            ),
            evidence=evidence,
        )

        print("Created evaluation job:", job.id)
        print("Initial status:", job.status)


if __name__ == "__main__":
    main()
