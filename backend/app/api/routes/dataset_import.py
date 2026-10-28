"""Offline, permission-gated dataset upload; no collection or publication."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.api.deps import require_source_manager
from app.core.database import get_db
from app.services.dataset_import import import_dataset

router = APIRouter(prefix='/admin/discovery', tags=['Dataset import'])


class DatasetUpload(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    source_key: str = Field(pattern=r'^[a-z0-9][a-z0-9_-]{0,99}$')
    filename: str = Field(min_length=1, max_length=255, pattern=r'^[^/\\\x00-\x1f]+$')
    approval_reference: str = Field(min_length=1, max_length=500)
    content_base64: str = Field(min_length=1, max_length=2_666_668)


@router.post('/dataset-imports')
def upload_dataset(body: DatasetUpload, actor=Depends(require_source_manager), db: Session = Depends(get_db)):
    return import_dataset(db, body, actor)
