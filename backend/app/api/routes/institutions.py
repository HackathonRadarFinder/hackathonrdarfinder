"""Bounded directory/coverage reads and audited review/import operations."""
from datetime import datetime
from typing import Annotated, Literal
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.deps import require_source_manager, require_reviewer
from app.core.database import get_db
from app.models.core import AuditLog
from app.models.institution import Institution, Announcement
from app.schemas.event import EventCreate
from app.schemas.institution import DirectoryImport
from app.services.database import database_operation
from app.services.institution_service import import_directory, coverage, verified_event_coverage
from app.services.announcement_review import review

router = APIRouter(tags=['Institution discovery'])


@router.get('/institutions/coverage')
def public_event_coverage(db: Session = Depends(get_db)):
    with database_operation(db):
        return verified_event_coverage(db)


@router.get('/institutions')
def institutions(q: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
                 state: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
                 page: Annotated[int, Query(ge=1, le=2147483647)] = 1,
                 page_size: Annotated[int, Query(ge=1, le=100)] = 100,
                 db: Session = Depends(get_db)):
    filters = [func.lower(Institution.state) == state.lower()] if state else []
    if q:
        filters.append(Institution.name.icontains(q, autoescape=True))
    with database_operation(db):
        rows = db.scalars(select(Institution).where(*filters).order_by(Institution.name, Institution.id)
            .offset((page - 1) * page_size).limit(page_size)).all()
        return dict(data=[dict(id=row.id, identifier=row.identifier, name=row.name, state=row.state,
            district=row.district, city=row.city, category=row.category, website=row.website,
            last_verified_at=row.last_verified_at, source_url=row.provenance['source_url']) for row in rows],
            total=db.scalar(select(func.count()).select_from(Institution).where(*filters)), page=page, page_size=page_size)


@router.put('/admin/discovery/institutions')
def directory_import(body: DirectoryImport, actor=Depends(require_source_manager), db: Session = Depends(get_db)):
    with database_operation(db):
        try:
            result = import_directory(db, body)
        except ValueError:
            db.rollback()
            raise HTTPException(422, 'Directory update conflicts with verified facts') from None
        db.add(AuditLog(user_id=uuid.UUID(actor.sub), action='institution_directory_imported', entity_type='directory',
            details=json.dumps(dict(provider=body.provider, source_url=body.source_url, counts=result))))
        db.commit()
        return result


@router.get('/admin/discovery/coverage', dependencies=[Depends(require_source_manager)])
def discovery_coverage(db: Session = Depends(get_db)):
    with database_operation(db):
        return coverage(db)


@router.get('/admin/discovery/announcements', dependencies=[Depends(require_reviewer)])
def announcements(status: Literal['pending', 'approved', 'rejected'] = 'pending',
                  page: Annotated[int, Query(ge=1, le=2147483647)] = 1,
                  db: Session = Depends(get_db)):
    with database_operation(db):
        query = select(Announcement).where(Announcement.status == status)
        rows = db.scalars(query.order_by(Announcement.observed_at.desc(), Announcement.id).offset((page-1)*50).limit(50)).all()
        return dict(data=[dict(id=row.id, institution_id=row.institution_id, status=row.status,
            payload=row.payload, evidence=row.evidence, observed_at=row.observed_at,
            last_seen_at=row.last_seen_at, review_note=row.review_note) for row in rows], page=page,
            total=db.scalar(select(func.count()).select_from(Announcement).where(Announcement.status == status)))


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    decision: Literal['approved', 'rejected']
    note: str = Field(min_length=10, max_length=2000)
    event: EventCreate | None = None

    @model_validator(mode='before')
    @classmethod
    def verified_dates(cls, value):
        if value.get('decision') == 'approved':
            event = value.get('event') or {}
            if isinstance(event, dict):
                for field in ('start_date', 'end_date', 'registration_deadline'):
                    raw = event.get(field)
                    if raw:
                        parsed = datetime.fromisoformat(raw.replace('Z', '+00:00')) if isinstance(raw, str) else raw
                        if not isinstance(parsed, datetime) or parsed.tzinfo is None:
                            raise ValueError('Review dates require an explicit timezone; do not invent missing times')
        return value


@router.post('/admin/discovery/announcements/{candidate_id}/review')
def review_announcement(candidate_id: uuid.UUID, body: ReviewDecision,
                        actor=Depends(require_reviewer), db: Session = Depends(get_db)):
    with database_operation(db):
        return review(db, candidate_id, body, actor)
