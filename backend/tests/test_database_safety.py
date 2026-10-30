from unittest.mock import Mock

import pytest
from sqlalchemy.engine import make_url

from scripts.prepare_test_database import validate_test_url, verify_test_connection


DEVELOPMENT = make_url("postgresql+psycopg://localhost/copilot_db")


@pytest.mark.parametrize("database", ["copilot_db", "postgres", "production", None])
def test_rejects_non_test_database(database):
    with pytest.raises(RuntimeError, match="unsafe"):
        validate_test_url(DEVELOPMENT.set(database=database), DEVELOPMENT, "copilot_test_db")


def test_rejects_development_database_even_if_named_as_test():
    target = DEVELOPMENT.set(database="copilot_test_db")
    with pytest.raises(RuntimeError, match="unsafe"):
        validate_test_url(target, target, "copilot_test_db")


def test_checks_connected_database_before_writes():
    connection = Mock()
    connection.engine.url = DEVELOPMENT.set(database="copilot_test_db")
    connection.execute.return_value.scalar_one.return_value = "copilot_db"
    with pytest.raises(RuntimeError, match="Connected database"):
        verify_test_connection(connection, DEVELOPMENT, "copilot_test_db")
    assert connection.execute.call_count == 1


def test_allows_explicit_disposable_database():
    target = DEVELOPMENT.set(database="copilot_test_db")
    assert validate_test_url(target, DEVELOPMENT, "copilot_test_db") == target
