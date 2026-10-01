from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.schemas.hackathon import HackathonCreate

router = APIRouter(
    prefix="/events",
    tags=["Events"]
)


@router.get("/")
def get_events(db: Session = Depends(get_db)):
    events = db.query(Hackathon).all()
    return {
        "message": "Events fetched successfully",
        "data": events
    }


@router.get("/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Hackathon).filter(Hackathon.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "message": "Event fetched successfully",
        "data": event
    }


@router.post("/")
def create_event(
    event: HackathonCreate,
    db: Session = Depends(get_db)
):
    organization = (
        db.query(Organization)
        .filter(Organization.name == event.organization)
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found. Create the organization first."
        )

    db_event = Hackathon(
        title=event.title,
        organization_id=organization.id,
        start_date=event.start_date,
        end_date=event.end_date,
        registration_deadline=event.registration_deadline,
        location=event.location,
        mode=event.mode,
        prize=event.prize,
        description=event.description,
        url=str(event.url) if event.url else None,
        source=event.source,
        scraped_at=event.scraped_at
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return {
        "message": "Event created successfully",
        "data": db_event
    }


@router.put("/{event_id}")
def update_event(
    event_id: int,
    event: HackathonCreate,
    db: Session = Depends(get_db)
):
    db_event = db.query(Hackathon).filter(Hackathon.id == event_id).first()

    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    organization = (
        db.query(Organization)
        .filter(Organization.name == event.organization)
        .first()
    )

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    db_event.title = event.title
    db_event.organization_id = organization.id
    db_event.start_date = event.start_date
    db_event.end_date = event.end_date
    db_event.registration_deadline = event.registration_deadline
    db_event.location = event.location
    db_event.mode = event.mode
    db_event.prize = event.prize
    db_event.description = event.description
    db_event.url = str(event.url) if event.url else None
    db_event.source = event.source
    db_event.scraped_at = event.scraped_at

    db.commit()
    db.refresh(db_event)

    return {
        "message": "Event updated successfully",
        "data": db_event
    }


@router.delete("/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Hackathon).filter(Hackathon.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event)
    db.commit()

    return {
        "message": "Event deleted successfully"
    }
