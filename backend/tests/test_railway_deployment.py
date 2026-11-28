"""Deployment regressions; no local PostgreSQL connection or provider access."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from workers import migrate


@pytest.mark.parametrize("prefix", ["postgres://", "postgresql://", "postgresql+psycopg://"])
def test_postgres_url_selects_installed_driver(prefix):
    tail = "u:p%40ss@private:5432/db?sslmode=require"
    settings = Settings(_env_file=None, DATABASE_URL=prefix + tail, SECRET_KEY="x" * 40)
    assert settings.DATABASE_URL == "postgresql+psycopg://" + tail


def test_sqlite_url_unchanged():
    settings = Settings(_env_file=None, DATABASE_URL="sqlite+pysqlite://", SECRET_KEY="x" * 40)
    assert settings.DATABASE_URL == "sqlite+pysqlite://"


@pytest.mark.parametrize("fails", [False, True])
def test_migration_uses_locked_connection_and_unlocks_on_failure(fails):
    connection = MagicMock()
    connection.dialect.name = "postgresql"
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    def upgrade(config, revision):
        assert config.attributes["connection"] is connection
        assert revision == "head"
        assert "pg_advisory_lock" in str(connection.execute.call_args_list[-1].args[0])
        if fails:
            raise RuntimeError("migration failed")
    with patch.object(migrate, "engine", engine), patch.object(migrate.command, "upgrade", side_effect=upgrade):
        if fails:
            with pytest.raises(RuntimeError, match="migration failed"):
                migrate.main()
        else:
            migrate.main()
    assert "pg_advisory_unlock" in str(connection.execute.call_args_list[-1].args[0])


def test_frontend_template_preserves_same_origin_and_dynamic_dns():
    root = Path(__file__).resolve().parents[2]
    template = (root / "frontend/nginx.conf").read_text()
    assert "rewrite ^/api/(.*)$ /$1 break;" in template
    assert "proxy_pass $backend_origin;" in template
    assert "valid=10s ipv6=off" in template
    assert 'Cache-Control "no-store"' in template
