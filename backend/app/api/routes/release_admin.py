"""Database-backed administrative controls with current-role authorization."""
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from app.api.deps import require_admin
from app.core.database import get_db
from app.services import release_admin

router = APIRouter(prefix='/admin', tags=['Admin operations'], dependencies=[Depends(require_admin)])


class RoleAssignment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['user', 'institution_coordinator', 'reviewer', 'source_manager', 'data_scientist', 'administrator']


@router.put('/users/{user_id}/role')
def change_role(user_id: UUID, body: RoleAssignment, actor=Depends(require_admin), db: Session = Depends(get_db)):
    return release_admin.assign_role(db, user_id, body.role, actor)


@router.get('/audit')
def audit(page: Annotated[int, Query(ge=1, le=2147483647)] = 1, db: Session = Depends(get_db)):
    return release_admin.audit_history(db, page)


@router.get('/notification-monitor')
def monitor(db: Session = Depends(get_db)):
    return release_admin.notification_monitor(db)
