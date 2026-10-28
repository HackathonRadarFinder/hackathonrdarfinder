from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.schemas.admin import AdminStats, AdminUserResponse
from app.schemas.event import EventResponse
from app.schemas.organization import OrganizationResponse
from app.schemas.responses import AdminDataResponse, DatabaseId, ERROR_RESPONSES, MessageResponse
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Admin"], responses=ERROR_RESPONSES)


@router.get("/status", response_model=MessageResponse)
async def admin_status():
    return {"message": "Admin API is ready"}


# Preserve the public readiness route. All new operations check the current
# database role through the existing AUTH-001 administrator dependency.
@router.get("/stats", response_model=AdminStats, dependencies=[Depends(require_admin)])
def get_admin_stats(db: Session = Depends(get_db)):
    return admin_service.get_admin_stats(db)


@router.get("/events", response_model=AdminDataResponse[list[EventResponse]], dependencies=[Depends(require_admin)])
def get_admin_events(db: Session = Depends(get_db)):
    return {"data": admin_service.get_all_events(db)}


@router.get("/organizations", response_model=AdminDataResponse[list[OrganizationResponse]], dependencies=[Depends(require_admin)])
def get_admin_organizations(db: Session = Depends(get_db)):
    return {"data": admin_service.get_all_organizations(db)}


@router.get("/users", response_model=AdminDataResponse[list[AdminUserResponse]], dependencies=[Depends(require_admin)])
def get_admin_users(db: Session = Depends(get_db)):
    return {"data": admin_service.get_all_users(db)}


@router.delete("/events/{event_id}", response_model=MessageResponse, dependencies=[Depends(require_admin)])
def delete_admin_event(event_id: DatabaseId, db: Session = Depends(get_db)):
    admin_service.delete_event(db, event_id)
    return {"message": "Event deleted successfully"}


@router.delete("/organizations/{organization_id}", response_model=MessageResponse, dependencies=[Depends(require_admin)])
def delete_admin_organization(organization_id: DatabaseId, db: Session = Depends(get_db)):
    admin_service.delete_organization(db, organization_id)
    return {"message": "Organization deleted successfully"}
