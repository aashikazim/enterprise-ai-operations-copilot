"""One-shot additive upgrade; never downgrade or delete existing data."""
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from app.db.database import engine


def main():
    # Initial vector columns predate extension provisioning in migrations.
    # Use a provisioning-capable local DB role; cloud roles should pre-create it.
    with engine.begin() as connection:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
    command.upgrade(Config('alembic.ini'), 'head')


if __name__ == '__main__':
    main()
