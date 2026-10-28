"""Administrator-only duplicate inspection and explicitly confirmed merging."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import require_admin
from app.core.database import get_db
from app.services.database import database_operation
from app.services.duplicate_review import candidate_pairs, merge_reviewed, MergeConflict

router = APIRouter(tags=['Duplicate review'])


class MergeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    survivor_id: int = Field(gt=0)
    duplicate_id: int = Field(gt=0)
    review_token: str = Field(pattern=r'^[a-f0-9]{64}$')
    note: str = Field(min_length=5, max_length=1000)


@router.get('/admin/duplicates')
def list_duplicates(limit: int = Query(100, ge=1, le=200), actor=Depends(require_admin), db: Session = Depends(get_db)):
    with database_operation(db):
        return candidate_pairs(db, limit=limit)


@router.post('/admin/duplicates/merge')
def merge_duplicates(body: MergeRequest, actor=Depends(require_admin), db: Session = Depends(get_db)):
    with database_operation(db):
        try:
            result = merge_reviewed(db, body.survivor_id, body.duplicate_id, body.review_token,
                                    UUID(actor.sub), body.note.strip())
            db.commit()
            return {'data': result}
        except (MergeConflict, IntegrityError) as exc:
            db.rollback()
            detail = str(exc) if isinstance(exc, MergeConflict) else 'Related data changed; refresh review before merging'
            raise HTTPException(409, detail) from None
