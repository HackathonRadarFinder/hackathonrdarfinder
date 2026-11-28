from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from prepare_deployment import validate_platform


def platform_env():
    return {
        "RENDER_BACKEND_URL": "https://radar-api.onrender.com",
        "CLOUDFLARE_FRONTEND_URL": "https://radar.pages.dev",
        "DATABASE_URL": "postgresql+psycopg://postgres:s3cret@db.abcdefghijkl.supabase.co:5432/postgres?sslmode=require",
        "SECRET_KEY": "k" * 40,
        "ENVIRONMENT": "production",
        "DEBUG": "false",
        "DISCOVERY_ENABLED": "true",
        "COLLECTOR_RAW_DATA_DIR": "/app/collector-data/raw",
        "INGESTION_INTERVAL_SECONDS": "3600",
        "WORKER_MAX_AGE_SECONDS": "7200",
    }


def test_valid_platform_configuration_is_accepted_without_leaking_secrets():
    result = validate_platform(platform_env())
    assert result["platform_configuration_valid"] is True
    assert result["render_backend_host"] == "radar-api.onrender.com"
    assert "s3cret" not in str(result) and "kkkk" not in str(result)


@pytest.mark.parametrize("key,value", [
    ("RENDER_BACKEND_URL", "http://radar-api.onrender.com"),
    ("RENDER_BACKEND_URL", "https://radar-api.example.invalid"),
    ("RENDER_BACKEND_URL", "https://user:pass@radar-api.onrender.com"),
    ("CLOUDFLARE_FRONTEND_URL", "https://radar-api.onrender.com"),
    ("CLOUDFLARE_FRONTEND_URL", ""),
    ("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/radar?sslmode=require"),
    ("DATABASE_URL", "postgresql+psycopg://u:p@db.abcdefghijkl.supabase.co:5432/postgres"),
    ("SECRET_KEY", "short"),
    ("ENVIRONMENT", "development"),
    ("DEBUG", "true"),
    ("DISCOVERY_ENABLED", "false"),
    ("COLLECTOR_RAW_DATA_DIR", "/tmp/raw"),
    ("WORKER_MAX_AGE_SECONDS", "3600"),
    ("INGESTION_INTERVAL_SECONDS", "hourly"),
])
def test_invalid_platform_configuration_is_rejected_without_echoing_values(key, value):
    env = platform_env()
    env[key] = value
    with pytest.raises(ValueError) as error:
        validate_platform(env)
    assert "s3cret" not in str(error.value) and "kkkk" not in str(error.value)
