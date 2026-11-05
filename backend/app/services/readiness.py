"""Read-only connectivity/head check, shared by HTTP readiness and safe startup."""
from pathlib import Path
from functools import lru_cache

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppException


@lru_cache
def expected_heads():
    config = Config()
    config.set_main_option('script_location', str(Path(__file__).resolve().parents[2] / 'database/migrations'))
    return frozenset(ScriptDirectory.from_config(config).get_heads())


def check_readiness(engine):
    try:
        with engine.connect() as connection:
            if connection.dialect.name == 'postgresql':
                connection.execute(text('SET TRANSACTION READ ONLY'))
                connection.execute(text("SET LOCAL statement_timeout = '1500ms'"))
            current = set(connection.scalars(text('SELECT version_num FROM alembic_version')))
        if current != expected_heads():
            raise AppException(code='SCHEMA_NOT_READY', message='Database migrations are required.', status_code=503)
    except SQLAlchemyError:
        raise AppException(code='DATABASE_NOT_READY', message='Database is unavailable or migrations are required.', status_code=503) from None
    return {'status': 'ready', 'database': 'connected', 'migrations': 'current'}
