from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime

# If app/db/base.py exists, import Base from there.
# Otherwise, we create a fallback declarative base so it won't crash.
try:
    from app.db.base import Base
except ImportError:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))