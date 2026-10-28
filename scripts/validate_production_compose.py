"""Validate private Compose configuration without printing secrets or connecting."""
import argparse
import json
from pathlib import Path
import re

from dotenv import dotenv_values
from sqlalchemy.engine import make_url


def validate(path, https=False):
    values = dotenv_values(path)
    for key, minimum in [('SECRET_KEY', 32), ('POSTGRES_PASSWORD', 16)]:
        value = values.get(key) or ''
        if len(value) < minimum or any(word in value.lower() for word in ('replace', 'placeholder', 'example', 'changeme')):
            raise ValueError('Set independent random production secrets')
    if values['SECRET_KEY'] == values['POSTGRES_PASSWORD']:
        raise ValueError('Use independent production secrets')
    url = make_url(values.get('DATABASE_URL') or '')
    if (url.drivername != 'postgresql+psycopg' or url.host != 'db' or url.port not in (None, 5432)
            or url.username != values.get('POSTGRES_USER') or url.password != values['POSTGRES_PASSWORD']
            or not url.database or url.database != values.get('POSTGRES_DB')):
        raise ValueError('Compose database configuration must agree and target its own db service')
    if https:
        domain = values.get('DOMAIN') or ''
        if (not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,63}', domain)
                or domain.endswith(('.invalid', '.example.com', '.example.org'))
                or domain in ('example.com', 'example.org')):
            raise ValueError('HTTPS needs an owner-controlled public DNS name')
    return {'configuration_valid': True, 'smtp_enabled': False, 'database_connected': False,
            'public_deployment': False, 'https_domain_configured': https}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--https', action='store_true')
    args = parser.parse_args()
    try:
        result = validate(args.env_file, args.https)
    except Exception:
        print('Invalid production configuration; check private secrets, matching database settings and real DNS name. No connection made.')
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
