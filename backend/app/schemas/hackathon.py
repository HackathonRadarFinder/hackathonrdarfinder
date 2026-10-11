from pydantic import BaseModel, ConfigDict, HttpUrl
from typing import Optional
from datetime import datetime


class HackathonBase(BaseModel):
    title: str
    organization: str

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None

    location: Optional[str] = None
    mode: Optional[str] = None

    prize: Optional[str] = None
    description: Optional[str] = None

    url: Optional[HttpUrl] = None
    source: Optional[str] = None

    scraped_at: Optional[datetime] = None


class HackathonCreate(HackathonBase):
    pass


class HackathonResponse(HackathonBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
