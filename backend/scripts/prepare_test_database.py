"""Provision only the two explicitly disposable Day 11A databases.

Run from backend: python -m scripts.prepare_test_database
Credentials are read from the environment/backend .env and never printed.
"""

import argparse
import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


TEST_DATABASES = ("copilot_test_db", "copilot_migration_test_db")


def development_url():
    values = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    value = os.environ.get("DATABASE_URL") or values.get("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is required for database safety checks")
    return make_url(value)


def validate_test_url(url, development, expected_database):
    url = make_url(url)
    development = make_url(development)
    if (
        expected_database not in TEST_DATABASES
        or url.database != expected_database
        or url.database == development.database
        or url.get_backend_name() != "postgresql"
    ):
        raise RuntimeError("Refusing an unsafe disposable database target")
    return url


def verify_test_connection(connection, development, expected_database):
    validate_test_url(connection.engine.url, development, expected_database)
    actual = connection.execute(text("SELECT current_database()")).scalar_one()
    if actual != expected_database:
        raise RuntimeError("Connected database does not match disposable target")


def provision(database):
    development = development_url()
    variable = (
        "TEST_DATABASE_URL" if database == TEST_DATABASES[0]
        else "MIGRATION_TEST_DATABASE_URL"
    )
    target = validate_test_url(
        os.environ.get(variable) or development.set(database=database),
        development,
        database,
    )
    # Database creation cannot run inside a transaction. The identifier is
    # restricted to TEST_DATABASES; credentials never enter SQL or stdout.
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database},
            ).scalar()
            if not exists:
                connection.exec_driver_sql(f'CREATE DATABASE "{database}"')
        engine = create_engine(target)
        try:
            with engine.begin() as connection:
                verify_test_connection(connection, development, database)
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                tables = connection.execute(text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "ORDER BY tablename"
                )).scalars().all()
                print(f"{database}: vector provisioned; public tables: {tables}")
        finally:
            engine.dispose()
    finally:
        admin.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", choices=TEST_DATABASES, default=TEST_DATABASES[0])
    args = parser.parse_args()
    try:
        provision(args.database)
    except Exception as exc:
        # Driver errors may contain connection credentials; do not echo them.
        raise SystemExit(f"Test database provisioning failed ({type(exc).__name__})") from None


if __name__ == "__main__":
    main()
