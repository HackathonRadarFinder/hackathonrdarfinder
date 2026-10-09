from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.organization import OrganizationCreate, OrganizationResponse
from app.services import organization_service


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)


@router.get("/")
def get_organizations(db: Session = Depends(get_db)):
    organizations = organization_service.get_organizations(db)

    return {
        "message": "Organizations fetched successfully",
        "data": organizations,
    }


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: int,
    db: Session = Depends(get_db),
):
    organization = organization_service.get_organization(
        db,
        organization_id,
    )

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    return organization


@router.post("/", response_model=OrganizationResponse)
def create_organization(
    organization: OrganizationCreate,
    db: Session = Depends(get_db),
):
    db_organization = organization_service.create_organization(
        db,
        organization,
    )

    if not db_organization:
        raise HTTPException(
            status_code=400,
            detail="Organization already exists",
        )

    return db_organization


@router.put("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: int,
    organization: OrganizationCreate,
    db: Session = Depends(get_db),
):
    db_organization = organization_service.update_organization(
        db,
        organization_id,
        organization,
    )

    if not db_organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    return db_organization


@router.delete("/{organization_id}")
def delete_organization(
    organization_id: int,
    db: Session = Depends(get_db),
):
    deleted = organization_service.delete_organization(
        db,
        organization_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    return {
        "message": "Organization deleted successfully",
    }