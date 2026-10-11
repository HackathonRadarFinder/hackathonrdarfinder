from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import EventVersion, Prediction, SavedItem
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.schemas.event import EventCreate
from app.services.database import database_operation


def _find_event(db: Session, event_id: int) -> Hackathon:
    event = db.get(Hackathon, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _event_values(db: Session, event: EventCreate) -> dict:
    if event.organization_id is not None:
        organization = db.get(Organization, event.organization_id)
    else:
        organization = db.scalar(select(Organization).where(Organization.name == event.organization))
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found. Create the organization first.")
    values = event.model_dump(exclude={"organization", "organization_id"})
    values["organization_id"] = organization.id
    values["url"] = str(event.url) if event.url is not None else None
    return values


def get_events(db: Session):
    with database_operation(db):
        return db.scalars(select(Hackathon).order_by(Hackathon.id)).all()


def get_event(db: Session, event_id: int):
    with database_operation(db):
        return _find_event(db, event_id)


def create_event(db: Session, event: EventCreate):
    with database_operation(db):
        record = Hackathon(**_event_values(db, event))
        db.add(record)
        db.commit()
        db.refresh(record)
        return record


def update_event(db: Session, event_id: int, event: EventCreate):
    with database_operation(db):
        record = _find_event(db, event_id)
        for key, value in _event_values(db, event).items():
            setattr(record, key, value)
        db.commit()
        db.refresh(record)
        return record


def delete_event(db: Session, event_id: int):
    with database_operation(db, "Event has related records and cannot be deleted"):
        record = _find_event(db, event_id)
        for model in (EventVersion, Prediction, SavedItem):
            if db.scalar(select(model.id).where(model.hackathon_id == event_id).limit(1)) is not None:
                raise HTTPException(status_code=409, detail="Event has related records and cannot be deleted")
        db.delete(record)
        db.commit()
        return True
