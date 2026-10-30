import os

from scripts.prepare_test_database import (
    development_url,
    validate_test_url,
    verify_test_connection,
)

DEVELOPMENT_DATABASE_URL = development_url()
TEST_DATABASE_URL = validate_test_url(
    os.environ.get("TEST_DATABASE_URL")
    or DEVELOPMENT_DATABASE_URL.set(database="copilot_test_db"),
    DEVELOPMENT_DATABASE_URL,
    "copilot_test_db",
)

# Set before importing the application or database module.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL.render_as_string(hide_password=False)
os.environ["JWT_SECRET_KEY"] = (
    "local-test-secret-not-for-production"
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import app
from app.db.models import Customer, User
from app.auth.security import hash_password, create_access_token
from app.db.rag_metric_model import RAGMetric  # register all tables for fixtures

engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def db():
    # This fixture resets the dedicated test database.
    # Never point it at your development or production DB.
    with engine.begin() as connection:
        verify_test_connection(connection, DEVELOPMENT_DATABASE_URL, "copilot_test_db")
        connection.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        Base.metadata.drop_all(bind=connection)
        Base.metadata.create_all(bind=connection)

    try:
        with TestSessionLocal() as session:
            yield session
    finally:
        with engine.begin() as connection:
            verify_test_connection(connection, DEVELOPMENT_DATABASE_URL, "copilot_test_db")
            Base.metadata.drop_all(bind=connection)


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()



@pytest.fixture
def test_customer(db):
    customer = Customer(
        name="Acme Corporation",
        email="acme@example.com",
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


@pytest.fixture
def test_admin(db, test_customer):
    admin = User(
        email="admin@acme.example",
        hashed_password=hash_password("TestPassword123!"),
        role="admin",
        customer_id=test_customer.id,
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    return admin


@pytest.fixture
def test_user(db, test_customer):
    user = User(
        email="user@acme.example",
        hashed_password=hash_password("TestPassword123!"),
        role="user",
        customer_id=test_customer.id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@pytest.fixture
def admin_headers(test_admin):
    token = create_access_token(test_admin.id)

    return {
        "Authorization": f"Bearer {token}"
    }


@pytest.fixture
def user_headers(test_user):
    token = create_access_token(test_user.id)

    return {
        "Authorization": f"Bearer {token}"
    }
