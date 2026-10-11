from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate
from app.services.database import database_operation


def _find_organization(db: Session, organization_id: int) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


def _check_name(db: Session, name: str, organization_id: int | None = None):
    query = select(Organization.id).where(Organization.name == name)
    if organization_id is not None:
        query = query.where(Organization.id != organization_id)
    if db.scalar(query) is not None:
        raise HTTPException(status_code=400, detail="Organization already exists")


def get_organizations(db: Session):
    with database_operation(db):
        return db.scalars(select(Organization).order_by(Organization.id)).all()


def get_organization(db: Session, organization_id: int):
    with database_operation(db):
        return _find_organization(db, organization_id)


def create_organization(db: Session, organization: OrganizationCreate):
    with database_operation(db, "Organization already exists", conflict_status=400):
        _check_name(db, organization.name)
        record = Organization(**organization.model_dump(mode="json"))
        db.add(record)
        db.commit()
        db.refresh(record)
        return record


def update_organization(db: Session, organization_id: int, organization: OrganizationCreate):
    with database_operation(db, "Organization already exists", conflict_status=400):
        record = _find_organization(db, organization_id)
        _check_name(db, organization.name, organization_id)
        for key, value in organization.model_dump(mode="json").items():
            setattr(record, key, value)
        db.commit()
        db.refresh(record)
        return record


def delete_organization(db: Session, organization_id: int):
    with database_operation(db, "Organization has events and cannot be deleted"):
        record = _find_organization(db, organization_id)
        if db.scalar(select(Hackathon.id).where(Hackathon.organization_id == organization_id).limit(1)) is not None:
            raise HTTPException(status_code=409, detail="Organization has events and cannot be deleted")
        db.delete(record)
        db.commit()
        return True
