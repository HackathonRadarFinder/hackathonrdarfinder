"""Fly MPG attaches PostgreSQL URLs; use installed psycopg 3 driver."""
import pytest

from app.core.database import normalize_database_url


@pytest.mark.parametrize(
    ("incoming", "expected"),
    [
        (
            "postgres://user:password@db.internal:5432/radar?sslmode=require",
            "postgresql+psycopg://user:password@db.internal:5432/radar?sslmode=require",
        ),
        (
            "postgresql://user:password@db.internal:5432/radar",
            "postgresql+psycopg://user:password@db.internal:5432/radar",
        ),
        (
            "postgresql+psycopg://user:password@db.internal:5432/radar",
            "postgresql+psycopg://user:password@db.internal:5432/radar",
        ),
        ("sqlite+pysqlite://", "sqlite+pysqlite://"),
    ],
)
def test_fly_database_url_driver(incoming, expected):
    assert normalize_database_url(incoming) == expected
