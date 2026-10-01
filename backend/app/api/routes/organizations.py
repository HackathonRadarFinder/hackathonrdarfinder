from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate

router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"]
)


@router.get("/")
def get_organizations(db: Session = Depends(get_db)):
    organizations = db.query(Organization).all()

    return {
        "message": "Organizations fetched successfully",
        "data": organizations
    }


@router.get("/{organization_id}")
def get_organization(
    organization_id: int,
    db: Session = Depends(get_db)
):
    organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id)
        .first()
    )

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "message": "Organization fetched successfully",
        "data": organization
    }


@router.post("/")
def create_organization(
    organization: OrganizationCreate,
    db: Session = Depends(get_db)
):
    existing = (
        db.query(Organization)
        .filter(Organization.name == organization.name)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Organization already exists"
        )

    db_organization = Organization(
        name=organization.name,
        website=str(organization.website) if organization.website else None,
        industry=organization.industry,
        location=organization.location,
        description=organization.description
    )

    db.add(db_organization)
    db.commit()
    db.refresh(db_organization)

    return {
        "message": "Organization created successfully",
        "data": db_organization
    }


@router.put("/{organization_id}")
def update_organization(
    organization_id: int,
    organization: OrganizationCreate,
    db: Session = Depends(get_db)
):
    db_organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id)
        .first()
    )

    if not db_organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    db_organization.name = organization.name
    db_organization.website = str(organization.website) if organization.website else None
    db_organization.industry = organization.industry
    db_organization.location = organization.location
    db_organization.description = organization.description

    db.commit()
    db.refresh(db_organization)

    return {
        "message": "Organization updated successfully",
        "data": db_organization
    }


@router.delete("/{organization_id}")
def delete_organization(
    organization_id: int,
    db: Session = Depends(get_db)
):
    organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id)
        .first()
    )

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    db.delete(organization)
    db.commit()

    return {
        "message": "Organization deleted successfully"
    }
