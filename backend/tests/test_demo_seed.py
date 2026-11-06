import pytest
from sqlalchemy import select, func
from app.db.models import Customer, User, Ticket
from app.auth.security import verify_password
from scripts.seed_demo import seed_demo, DEMO_EMAIL


def test_demo_seed_is_synthetic_and_refuses_overwrite(db):
    result = seed_demo(db, 'SyntheticDemoPassword123!')
    admin = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    assert verify_password('SyntheticDemoPassword123!', admin.hashed_password)
    assert db.get(Ticket, result['ticket_id']).customer_id == admin.customer_id
    assert db.get(Ticket, result['foreign_ticket_id']).customer_id != admin.customer_id
    db.commit()
    with pytest.raises(ValueError, match='refusing to overwrite'):
        seed_demo(db, 'AnotherSyntheticPassword123!')
    assert db.scalar(select(func.count()).select_from(Customer)) == 2
    assert db.scalar(select(func.count()).select_from(User)) == 1
    assert db.scalar(select(func.count()).select_from(Ticket)) == 2


def test_demo_rejects_short_password_without_writes(db):
    with pytest.raises(ValueError, match='at least 12'):
        seed_demo(db, 'short')
    assert db.scalar(select(func.count()).select_from(Customer)) == 0
