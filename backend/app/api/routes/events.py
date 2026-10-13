from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.schemas.event import EventCreate, EventListParams, EventListResponse, EventResponse
from app.schemas.responses import DatabaseId, DataResponse, ERROR_RESPONSES, MessageResponse
from app.services import event_service

router = APIRouter(prefix="/events", tags=["Events"], responses=ERROR_RESPONSES)


@router.get("/", response_model=EventListResponse | DataResponse[list[EventResponse]])
def get_events(
    query: Annotated[EventListParams, Query()],
    db: Session = Depends(get_db),
):
    """List all events for legacy callers, or opt in with any supported query parameter.

    Paginated responses retain message/data and add total, page and page_size.
    The defaults are page 1 and size 10 (maximum 100). Location and mode match
    literal, case-insensitive substrings; all supplied filters are combined.
    start_from and start_to are inclusive UTC calendar dates (YYYY-MM-DD).
    Events with an unknown start date are excluded only when a date filter is supplied.
    A page beyond the matching results returns an empty data list.
    """
    if any(value is not None for value in query.model_dump().values()):
        return {"message": "Events fetched successfully", **event_service.get_event_page(db, query)}
    return {"message": "Events fetched successfully", "data": event_service.get_events(db)}


@router.get("/{event_id}", response_model=DataResponse[EventResponse])
def get_event(event_id: DatabaseId, db: Session = Depends(get_db)):
    return {"message": "Event fetched successfully", "data": event_service.get_event(db, event_id)}


@router.post("/", response_model=DataResponse[EventResponse], dependencies=[Depends(require_admin)])
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    return {"message": "Event created successfully", "data": event_service.create_event(db, event)}


@router.put("/{event_id}", response_model=DataResponse[EventResponse], dependencies=[Depends(require_admin)])
def update_event(event_id: DatabaseId, event: EventCreate, db: Session = Depends(get_db)):
    return {"message": "Event updated successfully", "data": event_service.update_event(db, event_id, event)}


@router.delete("/{event_id}", response_model=MessageResponse, dependencies=[Depends(require_admin)])
def delete_event(event_id: DatabaseId, db: Session = Depends(get_db)):
    event_service.delete_event(db, event_id)
    return {"message": "Event deleted successfully"}
