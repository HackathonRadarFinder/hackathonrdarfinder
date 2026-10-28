from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Source
from app.schemas import SourceCreate, SourceUpdate


def get_source(
    db: Session,
    source_id: int
):
    return db.get(Source, source_id)


def get_source_by_url(
    db: Session,
    base_url: str
):
    statement = select(Source).where(
        Source.base_url == base_url
    )

    return db.scalar(statement)


def get_sources(
    db: Session,
    active_only: bool = False
):
    statement = select(Source)

    if active_only:
        statement = statement.where(
            Source.is_active.is_(True)
        )

    statement = statement.order_by(Source.priority.asc())

    return list(db.scalars(statement).all())


def create_source(
    db: Session,
    source_data: SourceCreate,
    robots_allowed: bool,
    robots_status: str
):
    source = Source(
        source_name=source_data.source_name,
        base_url=str(source_data.base_url),
        source_type=source_data.source_type,
        tier=source_data.tier,
        crawl_frequency=source_data.crawl_frequency,
        priority=source_data.priority,
        is_active=robots_allowed,
        robots_txt_allowed=robots_allowed,
        robots_txt_status=robots_status,
        created_by=source_data.created_by
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    return source


def update_source(
    db: Session,
    source: Source,
    source_data: SourceUpdate
):
    update_data = source_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)

    return source


def delete_source(
    db: Session,
    source: Source
):
    db.delete(source)
    db.commit()


def pause_source(
    db: Session,
    source: Source
):
    source.is_active = False

    db.commit()
    db.refresh(source)

    return source


def resume_source(
    db: Session,
    source: Source
):
    if not source.robots_txt_allowed:
        return None

    source.is_active = True

    db.commit()
    db.refresh(source)

    return source


def update_last_crawled(
    db: Session,
    source: Source
):
    source.last_crawled_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(source)

    return source