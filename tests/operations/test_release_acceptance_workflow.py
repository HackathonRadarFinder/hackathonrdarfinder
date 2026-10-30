"""Image publication must depend on real disposable PostgreSQL/browser acceptance."""
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]


def test_ci_runs_full_release_acceptance_and_uploads_evidence():
    workflow = yaml.load((ROOT / '.github/workflows/ci.yml').read_text(), Loader=yaml.BaseLoader)
    job = workflow['jobs']['docker-build']
    assert 'module24-test' in job['needs']
    commands = '\n'.join(step.get('run', '') for step in job['steps'])
    assert 'scripts/postgres_acceptance.py' in commands
    assert '--postgres-only' not in commands
    assert '--backend-image hackathon-radar-backend:test' in commands
    assert '--frontend-image hackathon-radar-frontend:test' in commands
    assert 'playwright-core install --with-deps chromium' in commands
    assert any(step.get('if') == 'always()' and step.get('with', {}).get('name') == 'release-acceptance-evidence' for step in job['steps'])
    assert 'release/**' in workflow['on']['push']['branches']
