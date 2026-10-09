from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.event import EventCreate, EventResponse
from app.services import event_service

router = APIRouter(
    prefix="/events",
    tags=["Events"]
)


@router.get("/", response_model=list[EventResponse])
def get_events(db: Session = Depends(get_db)):
    return event_service.get_events(db)


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = event_service.get_event(db, event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return event


@router.post("/", response_model=EventResponse)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    return event_service.create_event(db, event)


@router.put("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: int,
    event: EventCreate,
    db: Session = Depends(get_db)
):
    updated_event = event_service.update_event(db, event_id, event)

    if not updated_event:
        raise HTTPException(status_code=404, detail="Event not found")

    return updated_event

@router.delete("/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    deleted_event = event_service.delete_event(db, event_id)

    if not deleted_event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"message": "Event deleted successfully"}