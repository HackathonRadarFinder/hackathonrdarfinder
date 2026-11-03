"""Own a new loopback-only temporary PostgreSQL cluster when Docker is unavailable.

Never reuses an installed server, service, database or data directory. Credentials
are random/in-memory; only the one-time initdb password file exists briefly and
is removed before startup. The stopped disposable cluster is retained for review.
PostgreSQL 16 Docker acceptance remains the canonical CI gate.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]


def owned_directory(path, root, token):
    path, root = Path(path).resolve(), Path(root).resolve()
    if not path.is_relative_to(root) or path == root or path.is_symlink():
        raise RuntimeError('Refusing data directory outside the disposable acceptance root')
    marker = path / '.radar-acceptance-owner'
    if not marker.is_file() or marker.read_text(encoding='utf-8') != token:
        raise RuntimeError('Refusing data directory without matching ownership marker')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pg-bin', type=Path, required=True, help='Installed binaries only; no existing service is used')
    args = parser.parse_args()
    bin_dir = args.pg_bin.resolve()
    suffix = '.exe' if os.name == 'nt' else ''
    program = lambda name: str(bin_dir / (name + suffix))
    version = subprocess.run([program('postgres'), '--version'], capture_output=True, text=True, check=True).stdout
    if not any(f'PostgreSQL) {major}.' in version for major in (16, 18)):
        raise RuntimeError('Only PostgreSQL 16 or 18 is accepted by this disposable runner')
    major = 18 if 'PostgreSQL) 18.' in version else 16
    parent = ROOT / '.test-support/native-postgres'
    parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    output = Path(tempfile.mkdtemp(prefix=token[:12] + '-', dir=parent))
    data = output / 'data'
    password_file = output / 'init-password'
    password = secrets.token_urlsafe(32)
    password_file.write_text(password, encoding='utf-8')
    os.chmod(password_file, 0o600)
    started = False
    environment = dict(os.environ)
    for key in list(environment):
        if key.startswith('PG') or key in {'DATABASE_URL', 'RADAR_POSTGRES_ACCEPTANCE_URL', 'RADAR_POSTGRES_ACCEPTANCE_MANIFEST'}:
            environment.pop(key)

    def run(*command):
        # On Windows a daemon can inherit capture pipes and keep communicate()
        # waiting after pg_ctl exits. The owned server has its own log file.
        result = subprocess.run(command, env=environment, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=90)
        if result.returncode:
            raise RuntimeError(f'Disposable PostgreSQL {Path(command[0]).stem} failed; no external target used')

    try:
        try:
            run(program('initdb'), '-D', str(data), '-U', 'radar_acceptance', '--auth-host=scram-sha-256',
                '--auth-local=scram-sha-256', '--pwfile', str(password_file), '--encoding=UTF8', '--no-locale')
        finally:
            password_file.unlink(missing_ok=True)
        (data / '.radar-acceptance-owner').write_text(token, encoding='utf-8')
        owned_directory(data, parent, token)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        with (data / 'postgresql.conf').open('a', encoding='utf-8') as config:
            config.write(f"\nlisten_addresses = '127.0.0.1'\nport = {port}\nunix_socket_directories = ''\n")
        run(program('pg_ctl'), '-D', str(data), '-l', str(output / 'postgres.log'), '-w', 'start')
        started = True
        import psycopg
        from psycopg import sql
        database = 'radar_acceptance_' + token[:12]
        with psycopg.connect(host='127.0.0.1', port=port, dbname='postgres', user='radar_acceptance', password=password, autocommit=True) as connection:
            actual = connection.execute("SELECT current_setting('data_directory')").fetchone()[0]
            if Path(actual).resolve() != data.resolve():
                raise RuntimeError('Refusing a PostgreSQL process not owned by this run')
            connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
        from sqlalchemy import URL
        value = URL.create('postgresql+psycopg', username='radar_acceptance', password=password,
                           host='127.0.0.1', port=port, database=database).render_as_string(hide_password=False)
        manifest = dict(run_id=token, environment='development', database=database, storage='native-temporary',
            server_address='127.0.0.1', server_port=port, server_version_major=major,
            data_directory=str(data.resolve()), ownership_marker=token)
        manifest_path = output / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        test_env = dict(environment, RADAR_POSTGRES_ACCEPTANCE_URL=value,
            RADAR_POSTGRES_ACCEPTANCE_MANIFEST=str(manifest_path), EMAIL_MODE='disabled', DISCOVERY_ENABLED='false')
        with (output / 'tests.log').open('w', encoding='utf-8') as log:
            result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_postgres_acceptance.py', '-q',
                '--junitxml=' + str(output / 'results.xml')], cwd=ROOT / 'backend', env=test_env,
                stdout=log, stderr=subprocess.STDOUT, timeout=300)
        summary = dict(postgres_major=major, tests_exit_code=result.returncode, external_database_writes=False,
                       output=str(output.relative_to(ROOT)), cluster_stopped=False)
        (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print(json.dumps({key: value for key, value in summary.items() if key != 'cluster_stopped'}))
        return result.returncode
    finally:
        password_file.unlink(missing_ok=True)
        if started or (data / 'postmaster.pid').exists():
            owned_directory(data, parent, token)
            run(program('pg_ctl'), '-D', str(data), '-m', 'fast', '-w', 'stop')
            summary_path = output / 'summary.json'
            if summary_path.exists():
                summary = json.loads(summary_path.read_text(encoding='utf-8'))
                summary['cluster_stopped'] = True
                summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
