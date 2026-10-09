from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import admin_service


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get("/status")
def admin_status():
    return {
        "message": "Admin API is ready"
    }


@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
):
    return admin_service.get_admin_stats(db)


@router.get("/events")
def get_admin_events(
    db: Session = Depends(get_db),
):
    return {
        "data": admin_service.get_all_events(db)
    }


@router.get("/organizations")
def get_admin_organizations(
    db: Session = Depends(get_db),
):
    return {
        "data": admin_service.get_all_organizations(db)
    }


@router.get("/users")
def get_admin_users(
    db: Session = Depends(get_db),
):
    return {
        "data": admin_service.get_all_users(db)
    }


@router.delete("/events/{event_id}")
def delete_admin_event(
    event_id: int,
    db: Session = Depends(get_db),
):
    deleted = admin_service.delete_event(db, event_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    return {
        "message": "Event deleted successfully"
    }


@router.delete("/organizations/{organization_id}")
def delete_admin_organization(
    organization_id: int,
    db: Session = Depends(get_db),
):
    deleted = admin_service.delete_organization(
        db,
        organization_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    return {
        "message": "Organization deleted successfully"
    }