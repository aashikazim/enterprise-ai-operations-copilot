from app.api.evaluation_jobs import find_tenant_job
from app.jobs.evaluation_queue import enqueue_evaluation

# Use the Customer model from your existing project.
# Adjust the import path if necessary.
from app.db.models import Customer

def test_job_is_tenant_scoped(db):
    # 1. Create two valid customers.
    customer_a = Customer(
        name="Day10 Customer A",
        email="day10-customer-a@example.com",
    )

    customer_b = Customer(
        name="Day10 Customer B",
        email="day10-customer-b@example.com",
    )

    db.add_all([customer_a, customer_b])
    db.commit()

    db.refresh(customer_a)
    db.refresh(customer_b)

    # 2. Enqueue a job belonging to Customer A.
    job = enqueue_evaluation(
        db=db,
        customer_id=customer_a.id,
        question="What is MFA?",
        answer="MFA requires verification [Source 1].",
        evidence=[
            {
                "document_id": 1,
                "title": "MFA Policy",
                "content": "MFA requires verification.",
            }
        ],
    )

    # 3. Customer A should be able to access the job.
    assert find_tenant_job(
        db,
        job.id,
        customer_a.id,
    ) is not None

    # 4. Customer B must not be able to access the job.
    assert find_tenant_job(
        db,
        job.id,
        customer_b.id,
    ) is None