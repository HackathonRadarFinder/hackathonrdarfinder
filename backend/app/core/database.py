from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings


def normalize_database_url(url: str) -> str:
    """Use the installed psycopg 3 driver with Fly Managed Postgres URLs."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


database_url = normalize_database_url(settings.DATABASE_URL)
options = {'connect_args': {'connect_timeout': 2}, 'pool_timeout': 2} if database_url.startswith('postgresql+') else {}
engine = create_engine(database_url, pool_pre_ping=True, hide_parameters=True, **options)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
