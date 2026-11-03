"""Release skip/failure gates and review-only selected-platform configuration."""
from pathlib import Path
import json
import os
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]


def workflow(name):
    return yaml.load((ROOT / '.github/workflows' / name).read_text(encoding='utf-8'), Loader=yaml.BaseLoader)


def test_release_gate_rejects_failed_skipped_cancelled_and_missing_acceptance():
    ci = workflow('ci.yml')
    gate = ci['jobs']['release-gate']
    expected = {'backend-test', 'module24-test', 'frontend-test', 'fixture-portability',
                'pages-acceptance', 'infrastructure-check', 'docker-build'}
    assert set(gate['needs']) == expected and gate['if'] == 'always()'
    script = gate['steps'][0]['run'].split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    for bad in ('failure', 'skipped', 'cancelled', 'timed_out'):
        jobs = {name: {'result': 'success'} for name in expected}
        jobs['pages-acceptance']['result'] = bad
        result = subprocess.run([sys.executable, '-c', script],
            env={**os.environ, 'JOB_RESULTS': json.dumps(jobs)}, capture_output=True)
        assert result.returncode == 1
    result = subprocess.run([sys.executable, '-c', script],
        env={**os.environ, 'JOB_RESULTS': json.dumps({name: {'result': 'success'} for name in expected})}, capture_output=True)
    assert result.returncode == 0


def test_publisher_waits_for_whole_ci_and_all_deploys_verify_provenance():
    publish = workflow('build-and-publish.yml')
    assert publish['jobs']['validate']['uses'] == './.github/workflows/ci.yml'
    assert publish['jobs']['publish']['needs'] == 'validate'
    for name in ('deploy-dev.yml', 'deploy-test.yml', 'deploy-staging.yml', 'deploy-prod.yml'):
        value = workflow(name)
        assert set(value['on']) == {'workflow_dispatch'}
        commands = '\n'.join(step.get('run', '') for step in value['jobs']['deploy']['steps'])
        assert commands.index('scripts/verify_release.py') < commands.index('kubectl apply')


def test_prepared_render_backend_has_no_write_on_start_or_new_datastores():
    config = yaml.safe_load((ROOT / 'render.phase1.yaml').read_text(encoding='utf-8'))
    assert set(config) == {'services'} and len(config['services']) == 1
    backend = config['services'][0]
    assert backend['plan'] == 'free' and backend['runtime'] == 'docker'
    assert backend['healthCheckPath'] == '/ready' and backend['autoDeployTrigger'] == 'off'
    assert 'workers.check_ready' in backend['dockerCommand']
    assert 'workers.migrate' not in backend['dockerCommand'] and 'alembic' not in backend['dockerCommand']
    values = {item['key']: item for item in backend['envVars']}
    assert values['DATABASE_URL'] == {'key': 'DATABASE_URL', 'sync': False}
    assert values['SECRET_KEY'] == {'key': 'SECRET_KEY', 'sync': False}
    assert values['DISCOVERY_ENABLED']['value'] == 'false'


def test_ci_checks_fixture_portability_and_real_compiled_pages_runtime():
    ci = workflow('ci.yml')
    assert set(ci['jobs']['fixture-portability']['strategy']['matrix']['os']) == {'ubuntu-latest', 'windows-latest'}
    commands = '\n'.join(step.get('run', '') for step in ci['jobs']['pages-acceptance']['steps'])
    assert 'npm run build:pages' in commands and 'npm run test:pages' in commands
    assert 'deploy' not in commands
