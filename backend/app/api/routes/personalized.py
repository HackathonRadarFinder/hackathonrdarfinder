"""Private account preference storage and transparent catalog matching."""
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy.orm import Session
from app.api.deps import get_current_db_user
from app.core.database import get_db
from app.schemas.event import EventResponse
from app.services import personalized

router = APIRouter(prefix='/account', tags=['Personalization'])


class DiscoveryPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    preferred_location: str = Field(default='', max_length=100)
    preferred_mode: str = Field(default='', max_length=50)
    interests: str = Field(default='', max_length=255)
    in_app_reminders: StrictBool = True

    @field_validator('preferred_location', 'preferred_mode', 'interests')
    @classmethod
    def text_without_controls(cls, value):
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError('Preference text cannot contain control characters')
        return value


class Recommendation(BaseModel):
    event: EventResponse
    reasons: list[str]
    relevance_score: int


class Recommendations(BaseModel):
    data: list[Recommendation]
    method: str
    scanned: int
    truncated: bool
    message: str


@router.get('/discovery-preferences', response_model=DiscoveryPreferences)
def preferences(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    return personalized.get_preferences(db, user.id)


@router.put('/discovery-preferences', response_model=DiscoveryPreferences)
def save_preferences(body: DiscoveryPreferences, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    return personalized.update_preferences(db, user.id, body)


@router.get('/recommendations', response_model=Recommendations)
def recommendations(limit: Annotated[int, Query(ge=1, le=50)] = 12,
                    user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    return personalized.recommendations(db, user.id, limit)
