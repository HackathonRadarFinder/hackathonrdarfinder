"""Release-phase migrations, serialized across deployments on PostgreSQL."""
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.database import engine

LOCK_ID = 7241960321001


def main():
    config = Config("alembic.ini")
    with engine.connect() as connection:
        postgres = connection.dialect.name == "postgresql"
        if postgres:
            # Session lock survives Alembic transaction boundaries. Bound the wait.
            connection.execute(text("SET statement_timeout = '120s'"))
            connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": LOCK_ID})
            connection.commit()
        try:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        finally:
            if postgres:
                connection.rollback()
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_ID})
                connection.commit()


if __name__ == "__main__":
    main()
