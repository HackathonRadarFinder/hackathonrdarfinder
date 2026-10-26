"""Account-owned saved events and explicit email consent; no SMTP in requests."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, StrictBool, Field, field_validator
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.api.deps import get_current_db_user, get_current_user
from app.core.database import get_db
from app.models.core import Preference, SavedItem, Notification, AuditLog
from app.models.hackathon import Hackathon
from app.schemas.event import EventResponse
from app.schemas.user import UserResponse
from app.schemas.responses import DatabaseId, DataResponse, MessageResponse
from app.services.database import database_operation
from app.services.event_service import get_event, with_attribution

router = APIRouter(prefix="/account", tags=["Account"])


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)

    @field_validator('name')
    @classmethod
    def name_without_controls(cls, value):
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError('Display name cannot contain control characters')
        return value


@router.put('/profile', response_model=UserResponse)
def update_profile(body: ProfileUpdate, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    """Update the authenticated account's display name; identity and roles are immutable here."""
    with database_operation(db):
        profile = get_current_user(user)  # Validate the current role before any write.
        if user.name != body.name:
            user.name = body.name
            db.add(AuditLog(user_id=user.id, action='account_profile_updated', entity_type='user',
                entity_id=user.id, details='{"changed_fields":["name"]}'))
            db.commit()
        return {**profile, "name": user.name}


class ReminderPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email_reminders: StrictBool = False
    email_registration_reminders: StrictBool = True
    email_upcoming_reminders: StrictBool = True


@router.get("/saved", response_model=DataResponse[list[EventResponse]])
def saved_events(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    with database_operation(db):
        rows = db.scalars(select(Hackathon).join(SavedItem).where(
            SavedItem.user_id == user.id).order_by(Hackathon.id)).all()
        return {"message": "Saved events fetched", "data": with_attribution(db, rows)}


@router.put("/saved/{event_id}", response_model=MessageResponse)
def save_event(event_id: DatabaseId, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    event = get_event(db, event_id)
    with database_operation(db, "Event is already saved; refresh saved events"):
        if db.scalar(select(SavedItem.id).where(
                SavedItem.user_id == user.id, SavedItem.hackathon_id == event_id)) is None:
            db.add(SavedItem(user_id=user.id, hackathon_id=event_id))
            db.add(Notification(user_id=user.id, title="Event saved",
                                message=f"Saved {event.title}. Email reminders require your consent and an enabled worker."))
            db.commit()
        return {"message": "Event saved"}


@router.delete("/saved/{event_id}", response_model=MessageResponse)
def unsave_event(event_id: DatabaseId, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    with database_operation(db):
        db.execute(delete(SavedItem).where(SavedItem.user_id == user.id, SavedItem.hackathon_id == event_id))
        db.commit()
        return {"message": "Event removed from saved events"}


@router.get("/preferences", response_model=ReminderPreferences)
def preferences(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    with database_operation(db):
        values = dict(db.execute(select(Preference.key, Preference.value).where(
            Preference.user_id == user.id, Preference.key.in_(ReminderPreferences.model_fields))).all())
        return {key: values.get(key, "true" if field.default else "false") == "true"
                for key, field in ReminderPreferences.model_fields.items()}


@router.put("/preferences", response_model=ReminderPreferences)
def update_preferences(body: ReminderPreferences, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    with database_operation(db, "Preferences changed concurrently; reload and retry"):
        for key, value in body.model_dump().items():
            row = db.scalar(select(Preference).where(Preference.user_id == user.id, Preference.key == key))
            if row is None:
                row = Preference(user_id=user.id, key=key)
                db.add(row)
            row.value = "true" if value else "false"
        db.commit()
        return body
