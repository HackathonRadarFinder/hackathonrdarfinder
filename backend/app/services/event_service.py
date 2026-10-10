
from sqlalchemy.orm import Session
from app.models.hackathon import Hackathon
from app.schemas.event import EventCreate


def get_events(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    location: str | None = None,
    mode: str | None = None,
    organization_id: int | None = None,
):
    query = db.query(Hackathon)

    if location:
        query = query.filter(Hackathon.location.ilike(f"%{location}%"))

    if mode:
        query = query.filter(Hackathon.mode.ilike(f"%{mode}%"))

    if organization_id is not None:
        query = query.filter(
            Hackathon.organization_id == organization_id
        )

    total = query.count()

    items = (
        query.order_by(Hackathon.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_event(db: Session, event_id: int):
    return (
        db.query(Hackathon)
        .filter(Hackathon.id == event_id)
        .first()
    )


def create_event(db: Session, event: EventCreate):
    db_event = Hackathon(**event.model_dump())

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event


def update_event(db: Session, event_id: int, event: EventCreate):
    db_event = get_event(db, event_id)

    if not db_event:
        return None

    for field, value in event.model_dump().items():
        setattr(db_event, field, value)

    db.commit()
    db.refresh(db_event)

    return db_event


def delete_event(db: Session, event_id: int):
    db_event = get_event(db, event_id)

    if not db_event:
        return None

    db.delete(db_event)
    db.commit()

    return db_event
