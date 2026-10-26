"""Redacted configuration audit. Does not connect, start services, or alter .env."""
import json
import os
from pathlib import Path
import sys

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def audit():
    values = dotenv_values(ROOT / 'backend/.env')
    url = make_url(os.getenv('DATABASE_URL') or values['DATABASE_URL'])
    environment = os.getenv('ENVIRONMENT') or values.get('ENVIRONMENT')
    report = {'environment': environment, 'driver': url.drivername, 'host': url.host,
              'port': url.port, 'database': url.database, 'connected': False,
              'postgres_database_matches': values.get('POSTGRES_DB') == url.database,
              'postgres_user_matches': values.get('POSTGRES_USER') == url.username,
              'postgres_password_matches': values.get('POSTGRES_PASSWORD') == url.password,
              'process_debug_is_boolean': os.getenv('DEBUG', 'false').lower() in {'true', 'false', '0', '1'},
              'production_writes': False, 'secrets_in_report': False}
    report['blockers'] = []
    if environment != 'development':
        report['blockers'].append('Configured environment is not explicitly development')
    if not all(report[key] for key in ('postgres_database_matches', 'postgres_user_matches', 'postgres_password_matches')):
        report['blockers'].append('PostgreSQL initialization variables and application DATABASE_URL disagree; do not reset an existing volume to resolve this')
    if not report['process_debug_is_boolean']:
        report['blockers'].append('Host DEBUG is not boolean; use DEBUG=false for local commands')
    return report


if __name__ == '__main__':
    result = audit()
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result['blockers'] else 0)
