"""Inspect target identity without connecting or exposing credentials."""
from pathlib import Path
from sqlalchemy.engine import make_url


def inspect_target(database_url, environment, expected=None):
    url = make_url(database_url)
    database = url.database or ''
    reason = None
    if environment != 'development':
        reason = 'environment_is_not_development'
    elif any(word in database.lower() for word in ('production', 'prod')):
        reason = 'production_like_database_name'
    elif url.get_backend_name() == 'postgresql':
        if url.host not in {'db', 'localhost', '127.0.0.1', '::1'}:
            reason = 'remote_database_not_authorized'
    elif url.get_backend_name() == 'sqlite':
        if database in {'', ':memory:'}:
            reason = 'memory_database_not_a_development_import_target'
        else:
            database = str(Path(database).resolve())
    else:
        reason = 'unsupported_development_dialect'
    if expected is not None:
        expected = str(Path(expected).resolve()) if url.get_backend_name() == 'sqlite' else expected
        if expected != database:
            reason = 'expected_database_mismatch'
    return {'environment': environment, 'driver': url.drivername, 'host': url.host,
            'database': database, 'development_config_verified': reason is None,
            'server_identity_verified': False, 'connected': False, 'block_reason': reason}


def require_development_target(database_url, environment, expected):
    if not expected:
        raise ValueError('--apply requires --expect-database to bind the development target')
    result = inspect_target(database_url, environment, expected)
    if not result['development_config_verified']:
        raise ValueError('Development target refused: ' + result['block_reason'])
    return result
