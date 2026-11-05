import os
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.db.database import Base, get_settings
from conftest import DEVELOPMENT_DATABASE_URL
from scripts.prepare_test_database import validate_test_url, verify_test_connection


def test_fresh_migrations_match_models(monkeypatch):
    """Exercise historical migrations plus the repair on a separate disposable DB."""
    target = validate_test_url(
        os.environ.get("MIGRATION_TEST_DATABASE_URL")
        or DEVELOPMENT_DATABASE_URL.set(database="copilot_migration_test_db"),
        DEVELOPMENT_DATABASE_URL,
        "copilot_migration_test_db",
    )
    engine = create_engine(target)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    try:
        with engine.begin() as connection:
            verify_test_connection(connection, DEVELOPMENT_DATABASE_URL, "copilot_migration_test_db")
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        with monkeypatch.context() as environment:
            environment.setenv("DATABASE_URL", target.render_as_string(hide_password=False))
            get_settings.cache_clear()
            # This database belongs exclusively to this migration test. Reset
            # via migrations so repeated suite runs exercise the entire chain.
            command.downgrade(config, "base")
            assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
            command.upgrade(config, "head")
            command.upgrade(config, "head")
            with engine.connect() as connection:
                assert connection.execute(text("SELECT extversion FROM pg_extension WHERE extname='vector'")).scalar()
                assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == ScriptDirectory.from_config(config).get_current_head()
                assert connection.execute(text(
                    "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                    "WHERE attrelid='document_chunks'::regclass AND attname='embedding'"
                )).scalar_one() == "vector(384)"
                assert set(inspect(connection).get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
                assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
                indexes = inspect(connection).get_indexes("rag_metrics")
                assert any(i["name"] == "ix_rag_metrics_request_id" and i["unique"] for i in indexes)
                assert any(i["name"] == "ix_rag_metrics_customer_id" for i in indexes)
                assert any(i["name"] == "ix_document_chunks_content_fts" for i in inspect(connection).get_indexes("document_chunks"))
                assert any(i["name"] == "ix_evaluation_jobs_queue" for i in inspect(connection).get_indexes("evaluation_jobs"))
            # Prove the repair is additive to the historical Day 10 head too.
            command.downgrade(config, "fa8c76d8e74e")
            assert "rag_metrics" not in inspect(engine).get_table_names()
            command.upgrade(config, "head")
    finally:
        get_settings.cache_clear()
        engine.dispose()
