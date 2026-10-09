from sqlalchemy.orm import Session

from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.models.core import User


def get_admin_stats(db: Session):
    return {
        "total_events": db.query(Hackathon).count(),
        "total_organizations": db.query(Organization).count(),
        "total_users": db.query(User).count(),
    }


def get_all_events(db: Session):
    return db.query(Hackathon).all()


def get_all_organizations(db: Session):
    return db.query(Organization).all()


def get_all_users(db: Session):
    return db.query(User).all()


def delete_event(db: Session, event_id: int):
    event = (
        db.query(Hackathon)
        .filter(Hackathon.id == event_id)
        .first()
    )

    if not event:
        return False

    db.delete(event)
    db.commit()
    return True


def delete_organization(db: Session, organization_id: int):
    organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id)
        .first()
    )

    if not organization:
        return False

    db.delete(organization)
    db.commit()
    return True