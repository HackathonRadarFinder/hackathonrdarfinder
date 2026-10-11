from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.schemas.organization import OrganizationCreate, OrganizationResponse
from app.schemas.responses import DatabaseId, DataResponse, ERROR_RESPONSES, MessageResponse
from app.services import organization_service

router = APIRouter(prefix="/organizations", tags=["Organizations"], responses=ERROR_RESPONSES)


@router.get("/", response_model=DataResponse[list[OrganizationResponse]])
def get_organizations(db: Session = Depends(get_db)):
    return {"message": "Organizations fetched successfully", "data": organization_service.get_organizations(db)}


@router.get("/{organization_id}", response_model=DataResponse[OrganizationResponse])
def get_organization(organization_id: DatabaseId, db: Session = Depends(get_db)):
    return {"message": "Organization fetched successfully", "data": organization_service.get_organization(db, organization_id)}


@router.post("/", response_model=DataResponse[OrganizationResponse], dependencies=[Depends(require_admin)])
def create_organization(organization: OrganizationCreate, db: Session = Depends(get_db)):
    return {"message": "Organization created successfully", "data": organization_service.create_organization(db, organization)}


@router.put("/{organization_id}", response_model=DataResponse[OrganizationResponse], dependencies=[Depends(require_admin)])
def update_organization(organization_id: DatabaseId, organization: OrganizationCreate, db: Session = Depends(get_db)):
    return {"message": "Organization updated successfully", "data": organization_service.update_organization(db, organization_id, organization)}


@router.delete("/{organization_id}", response_model=MessageResponse, dependencies=[Depends(require_admin)])
def delete_organization(organization_id: DatabaseId, db: Session = Depends(get_db)):
    organization_service.delete_organization(db, organization_id)
    return {"message": "Organization deleted successfully"}
