"""Own a disposable PostgreSQL 16 container and test only that verified target.

No existing Compose service, database, volume or password is changed. Generated
credentials stay in process environments and are never written to reports.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def docker(*args, env=None):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, env=env, timeout=300)
    if result.returncode:
        raise RuntimeError('Docker operation failed: ' + args[0])
    return result.stdout.strip()


def inspect_container(name, run_id):
    info = json.loads(docker('inspect', name))[0]
    if info['Config']['Labels'].get('radar.acceptance.id') != run_id:
        raise RuntimeError('Refusing a container not owned by this acceptance run')
    return info


def port_for(info, container_port):
    binding = info['NetworkSettings']['Ports'][f'{container_port}/tcp'][0]
    if binding['HostIp'] != '127.0.0.1':
        raise RuntimeError('Acceptance ports must bind loopback only')
    return int(binding['HostPort'])


def wait_http(url):
    for _ in range(120):
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return json.load(response)
        except (OSError, ValueError):
            pass
        time.sleep(0.5)
    raise RuntimeError('Acceptance HTTP readiness timeout')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / '.test-support/readiness')
    parser.add_argument('--postgres-only', action='store_true', help='Skip built-image/browser checks')
    parser.add_argument('--container-tests', action='store_true', help='Run PostgreSQL tests in the backend image instead of the host Python environment')
    parser.add_argument('--backend-image', default='radar-backend-acceptance:readiness-20261025')
    parser.add_argument('--frontend-image', default='radar-frontend-acceptance:readiness-20261025')
    args = parser.parse_args()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    name = 'radar-pg-acceptance-' + run_id
    network = 'radar-acceptance-' + run_id
    database = 'radar_acceptance_' + run_id
    password = secrets.token_urlsafe(32)
    owned = []
    report = {'run_id': run_id, 'environment': 'development', 'database': database,
              'production_or_existing_development_writes': False, 'human_approval_claimed': False}
    network_created = False
    try:
        docker('network', 'create', '--label', 'radar.acceptance.id=' + run_id, network)
        network_created = True
        environment = dict(os.environ, POSTGRES_PASSWORD=password)
        docker('run', '--detach', '--name', name, '--label', 'radar.acceptance.id=' + run_id,
               '--network', network, '--network-alias', 'db', '--publish', '127.0.0.1::5432',
               '--tmpfs', '/var/lib/postgresql/data:rw', '--env', 'POSTGRES_PASSWORD',
               '--env', 'POSTGRES_USER=radar_acceptance', '--env', 'POSTGRES_DB=' + database,
               'postgres:16-alpine', env=environment)
        owned.append(name)
        info = inspect_container(name, run_id)
        if '/var/lib/postgresql/data' not in info['HostConfig']['Tmpfs']:
            raise RuntimeError('Disposable PostgreSQL must use tmpfs')
        if any(mount['Type'] == 'volume' for mount in info.get('Mounts', [])):
            raise RuntimeError('Acceptance must not create or use persistent volumes')
        port = port_for(info, 5432)
        address = info['NetworkSettings']['Networks'][network]['IPAddress']
        for _ in range(120):
            result = subprocess.run(['docker', 'exec', name, 'pg_isready', '-h', '127.0.0.1', '-U', 'radar_acceptance',
                                     '-d', database], capture_output=True)
            if result.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError('Disposable PostgreSQL readiness timeout')
        manifest = {'run_id': run_id, 'container_id': info['Id'], 'ownership_label': run_id,
                    'environment': 'development', 'database': database, 'storage': 'tmpfs',
                    'server_address': address, 'host': '127.0.0.1', 'host_port': port}
        manifest_path = output / 'postgres_manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        # These imports have no application/database side effects.
        sys.path.insert(0, str(ROOT / 'backend'))
        from sqlalchemy.engine import URL
        host_url = URL.create('postgresql+psycopg', username='radar_acceptance', password=password,
                              host='127.0.0.1', port=port, database=database).render_as_string(hide_password=False)
        test_environment = dict(os.environ, RADAR_POSTGRES_ACCEPTANCE_URL=host_url,
                                RADAR_POSTGRES_ACCEPTANCE_MANIFEST=str(manifest_path), DEBUG='false')
        if args.container_tests:
            test_environment['RADAR_POSTGRES_ACCEPTANCE_URL'] = URL.create(
                'postgresql+psycopg', username='radar_acceptance', password=password,
                host='db', port=5432, database=database).render_as_string(hide_password=False)
            test_environment['RADAR_POSTGRES_ACCEPTANCE_MANIFEST'] = '/evidence/postgres_manifest.json'
            test_container = 'radar-tests-acceptance-' + run_id
            test_command = ['docker', 'run', '--rm', '--name', test_container, '--label', 'radar.acceptance.id=' + run_id,
                '--network', network, '--security-opt', 'no-new-privileges:true', '--cap-drop', 'ALL',
                '--mount', f'type=bind,source={ROOT},target=/workspace,readonly',
                '--mount', f'type=bind,source={output},target=/evidence',
                '--workdir', '/workspace/backend', '--env', 'RADAR_POSTGRES_ACCEPTANCE_URL',
                '--env', 'RADAR_POSTGRES_ACCEPTANCE_MANIFEST', '--env', 'DEBUG=false',
                args.backend_image, 'python', '-m', 'pytest', 'tests/test_postgres_acceptance.py',
                '-q', '-p', 'no:cacheprovider', '--basetemp=/tmp/radar-pytest',
                '--junitxml=/evidence/postgres-tests.xml']
        else:
            test_command = [sys.executable, '-m', 'pytest', 'tests/test_postgres_acceptance.py', '-q',
                            '--junitxml', str(output / 'postgres-tests.xml')]
        try:
            tests = subprocess.run(test_command, cwd=ROOT / 'backend', env=test_environment,
                                   capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            if args.container_tests:
                inspect_container(test_container, run_id)
                docker('stop', '--time', '5', test_container)
            raise RuntimeError('Acceptance tests exceeded 300 seconds') from None
        log = (tests.stdout + '\n' + tests.stderr).replace(password, '[REDACTED]')
        (output / 'postgres-tests.log').write_text(log, encoding='utf-8')
        print(log, flush=True)
        if tests.returncode:
            raise RuntimeError('Disposable PostgreSQL acceptance tests failed')
        suites = ET.parse(output / 'postgres-tests.xml').getroot().findall('testsuite')
        summary = {key: sum(int(suite.get(key, 0)) for suite in suites)
                   for key in ('tests', 'failures', 'errors', 'skipped')}
        if not summary['tests'] or summary['skipped']:
            raise RuntimeError('PostgreSQL acceptance must execute, not skip, its checks')
        report['postgres_tests'] = summary
        report['identity_verified_before_migrations'] = True
        if not args.postgres_only:
            backend = 'radar-backend-acceptance-' + run_id
            frontend = 'radar-frontend-acceptance-' + run_id
            internal_url = URL.create('postgresql+psycopg', username='radar_acceptance', password=password,
                                      host='db', port=5432, database=database).render_as_string(hide_password=False)
            service_environment = dict(os.environ, DATABASE_URL=internal_url,
                SECRET_KEY=secrets.token_urlsafe(48), ENVIRONMENT='development', DEBUG='false',
                EMAIL_MODE='disabled', DISCOVERY_ENABLED='false', LOG_LEVEL='WARNING')
            options = []
            for key in ('DATABASE_URL', 'SECRET_KEY', 'ENVIRONMENT', 'DEBUG', 'EMAIL_MODE', 'DISCOVERY_ENABLED', 'LOG_LEVEL'):
                options += ['--env', key]
            docker('run', '--detach', '--name', backend, '--label', 'radar.acceptance.id=' + run_id,
                   '--network', network, '--network-alias', 'acceptance-api', '--publish', '127.0.0.1::8000',
                   '--security-opt', 'no-new-privileges:true', '--cap-drop', 'ALL',
                   *options, args.backend_image, env=service_environment)
            owned.append(backend)
            backend_info = inspect_container(backend, run_id)
            api_base = f'http://127.0.0.1:{port_for(backend_info, 8000)}'
            assert wait_http(api_base + '/health')['status'] == 'healthy'
            result = wait_http(api_base + '/events/?page=1&page_size=1')
            assert result['total'] == 1 and result['data'][0]['title'] == 'Hacknauts 2.0'
            docker('run', '--detach', '--name', frontend, '--label', 'radar.acceptance.id=' + run_id,
                   '--network', network, '--publish', '127.0.0.1::8080',
                   '--env', 'BACKEND_HOST=acceptance-api',
                   '--security-opt', 'no-new-privileges:true', '--cap-drop', 'ALL', args.frontend_image)
            owned.append(frontend)
            frontend_info = inspect_container(frontend, run_id)
            ui_base = f'http://127.0.0.1:{port_for(frontend_info, 8080)}'
            assert wait_http(ui_base + '/api/health')['status'] == 'healthy'
            assert wait_http(ui_base + '/api/events/?page=1&page_size=1')['total'] == 1
            with urlopen(ui_base + '/api/health', timeout=5) as response:
                assert response.headers['Cache-Control'] == 'no-store'
            collector_result = docker('run', '--rm', '--label', 'radar.acceptance.id=' + run_id,
                   '--user', '0', '--tmpfs', '/app/collector-data:rw,nosuid,noexec',
                   '--security-opt', 'no-new-privileges:true', '--cap-drop', 'ALL',
                   '--cap-add', 'CHOWN', '--cap-add', 'SETUID', '--cap-add', 'SETGID',
                   '--env', 'DISCOVERY_ENABLED=false',
                   '--env', 'COLLECTOR_SNAPSHOT_DIR=/app/collector-data',
                   '--env', 'COLLECTOR_RAW_DATA_DIR=/app/collector-data/raw',
                   args.backend_image, 'python', '-m', 'workers.railway_collector')
            assert json.loads(collector_result) == {'enabled': False, 'executed': False}
            report['collector_mount_init_privilege_drop_disabled_collection'] = 'passed'
            browser = subprocess.run(['node', 'tests/postgres.browser.mjs'], cwd=ROOT / 'frontend',
                env=dict(os.environ, RADAR_ACCEPTANCE_UI=ui_base, RADAR_ACCEPTANCE_RUN_ID=run_id,
                         RADAR_ACCEPTANCE_ARTIFACT=str(output / 'container-browser')),
                capture_output=True, text=True, timeout=120)
            (output / 'container-browser.log').write_text(browser.stdout + '\n' + browser.stderr, encoding='utf-8')
            if browser.returncode:
                raise RuntimeError('Built-image PostgreSQL browser acceptance failed')
            report['built_image_health_and_events'] = 'passed'
            report['container_browser'] = 'passed'
            report['image_ids'] = {'backend': backend_info['Image'], 'frontend': frontend_info['Image']}
            report['runtime_users'] = {'backend': backend_info['Config']['User'],
                                       'frontend': frontend_info['Config']['User']}
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed'
        report['failure'] = str(exc).replace(password, '[REDACTED]')
        raise
    finally:
        cleanup = []
        for container in reversed(owned):
            inspect_container(container, run_id)
            docker('stop', '--time', '10', container)
            docker('rm', container)  # Deliberately no -v and no volume deletion.
            cleanup.append(container)
        if network_created:
            metadata = json.loads(docker('network', 'inspect', network))[0]
            if metadata['Labels'].get('radar.acceptance.id') != run_id:
                raise RuntimeError('Refusing an unowned Docker network')
            docker('network', 'rm', network)
        report['owned_containers_removed'] = cleanup
        report['persistent_volumes_deleted'] = False
        (output / 'postgres_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
