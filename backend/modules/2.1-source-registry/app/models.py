from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    source_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    source_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    base_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        index=True
    )

    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    tier: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )

    crawl_frequency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="24h"
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    robots_txt_allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    robots_txt_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="unknown"
    )

    last_crawled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )