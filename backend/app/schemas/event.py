from pydantic import BaseModel,ConfigDict
from typing import Optional
from datetime import datetime

class EventBase(BaseModel):
    title: str
    organization_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    location: Optional[str] = None
    mode: Optional[str] = None
    prize: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    scraped_at: Optional[datetime] = None

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
