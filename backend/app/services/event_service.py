from sqlalchemy.orm import Session
from app.models.hackathon import Hackathon
from app.schemas.event import EventCreate

def get_events(db: Session):
    return db.query(Hackathon).all()


def get_event(db: Session, event_id: int):
    return db.query(Hackathon).filter(Hackathon.id == event_id).first()

def create_event(db: Session, event: EventCreate):
    db_event = Hackathon(
        title=event.title,
        organization_id=event.organization_id,
        start_date=event.start_date,
        end_date=event.end_date,
        registration_deadline=event.registration_deadline,
        location=event.location,
        mode=event.mode,
        prize=event.prize,
        description=event.description,
        url=event.url,
        source=event.source,
        scraped_at=event.scraped_at,
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event


def update_event(db: Session, event_id: int, event: EventCreate):
    db_event = db.query(Hackathon).filter(Hackathon.id == event_id).first()

    if not db_event:
        return None

    db_event.title = event.title
    db_event.organization_id = event.organization_id
    db_event.start_date = event.start_date
    db_event.end_date = event.end_date
    db_event.registration_deadline = event.registration_deadline
    db_event.location = event.location
    db_event.mode = event.mode
    db_event.prize = event.prize
    db_event.description = event.description
    db_event.url = event.url
    db_event.source = event.source
    db_event.scraped_at = event.scraped_at

    db.commit()
    db.refresh(db_event)

    return db_event



def delete_event(db: Session, event_id: int):
    db_event = db.query(Hackathon).filter(Hackathon.id == event_id).first()

    if not db_event:
        return None

    db.delete(db_event)
    db.commit()

    return db_event
