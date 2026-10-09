from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate


def get_organizations(db: Session):
    return db.query(Organization).all()


def get_organization(db: Session, organization_id: int):
    return (
        db.query(Organization)
        .filter(Organization.id == organization_id)
        .first()
    )


def create_organization(db: Session, organization: OrganizationCreate):
    existing = (
        db.query(Organization)
        .filter(Organization.name == organization.name)
        .first()
    )

    if existing:
        return None

    db_organization = Organization(
        name=organization.name,
        website=str(organization.website) if organization.website else None,
        industry=organization.industry,
        location=organization.location,
        description=organization.description,
    )

    db.add(db_organization)
    db.commit()
    db.refresh(db_organization)

    return db_organization


def update_organization(
    db: Session,
    organization_id: int,
    organization: OrganizationCreate,
):
    db_organization = get_organization(db, organization_id)

    if not db_organization:
        return None

    db_organization.name = organization.name
    db_organization.website = (
        str(organization.website) if organization.website else None
    )
    db_organization.industry = organization.industry
    db_organization.location = organization.location
    db_organization.description = organization.description

    db.commit()
    db.refresh(db_organization)

    return db_organization


def delete_organization(db: Session, organization_id: int):
    db_organization = get_organization(db, organization_id)

    if not db_organization:
        return False

    db.delete(db_organization)
    db.commit()

    return True