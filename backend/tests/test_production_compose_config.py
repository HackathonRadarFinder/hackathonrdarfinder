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
