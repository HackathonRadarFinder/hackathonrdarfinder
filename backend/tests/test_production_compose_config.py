from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from validate_production_compose import validate


@pytest.fixture
def config(tmp_path):
    path = tmp_path / '.env'
    path.write_text('POSTGRES_USER=test\nPOSTGRES_DB=isolated_test\n'
        'POSTGRES_PASSWORD=0123456789abcdef0123456789abcdef\n'
        'SECRET_KEY=fedcba9876543210fedcba9876543210\n'
        'DATABASE_URL=postgresql+psycopg://test:0123456789abcdef0123456789abcdef@db:5432/isolated_test\n'
        'DOMAIN=radar.example.invalid\n', encoding='utf-8')
    return path


def test_no_smtp_configuration_required(config):
    result = validate(config)
    assert result['configuration_valid'] and not result['smtp_enabled']
    assert not result['database_connected'] and not result['public_deployment']
    assert '0123456789' not in str(result)


@pytest.mark.parametrize('change', ['placeholder', 'external_database', 'mismatch', 'placeholder_domain'])
def test_invalid_production_targets_and_placeholders_refused(config, change):
    content = config.read_text()
    if change == 'placeholder':
        content = content.replace('fedcba9876543210fedcba9876543210', 'REPLACE_WITH_SECRET_AT_LEAST_32_CHARACTERS')
    elif change == 'external_database':
        content = content.replace('@db:', '@production.example.org:')
    elif change == 'mismatch':
        content = content.replace('POSTGRES_USER=test', 'POSTGRES_USER=other')
    config.write_text(content)
    with pytest.raises(ValueError):
        validate(config, https=change == 'placeholder_domain')


def test_organizer_raw_snapshots_use_the_persistent_collector_directory():
    import yaml
    from unittest.mock import patch
    import os
    collector_path = Path(__file__).resolve().parents[1] / 'modules/2.2-collector/src'
    sys.path.insert(0, str(collector_path))
    from collector_engine.config.loader import Settings
    root = Path(__file__).resolve().parents[2]
    for filename in ('docker-compose.yml', 'docker-compose.production.yml'):
        collector = yaml.safe_load((root / filename).read_text(encoding='utf-8'))['services']['collector']
        environment = collector['environment']
        assert 'RAW_DATA_DIR' not in environment
        with patch.dict(os.environ, environment, clear=True):
            directory = Settings.from_env().raw_data_dir
        assert directory == Path('/app/collector-data/raw')
        assert any(volume.split(':')[1] == '/app/collector-data' for volume in collector['volumes'])
