from sqlalchemy import func, select
from sqlalchemy.orm import Session, load_only, selectinload

from app.models.core import Role, User
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.services import event_service, organization_service
from app.services.database import database_operation


def get_admin_stats(db: Session):
    with database_operation(db):
        return {
            "total_events": db.scalar(select(func.count()).select_from(Hackathon)),
            "total_organizations": db.scalar(select(func.count()).select_from(Organization)),
            "total_users": db.scalar(select(func.count()).select_from(User)),
        }


def get_all_events(db: Session):
    return event_service.get_events(db)


def get_all_organizations(db: Session):
    return organization_service.get_organizations(db)


def get_all_users(db: Session):
    with database_operation(db):
        users = db.scalars(select(User).options(
            load_only(User.id, User.name, User.email, User.status, User.created_at),
            selectinload(User.roles).load_only(Role.name),
        ).order_by(User.created_at, User.id)).all()
        return [{
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "status": user.status,
            "created_at": user.created_at,
            "roles": sorted(role.name for role in user.roles),
        } for user in users]


def delete_event(db: Session, event_id: int):
    return event_service.delete_event(db, event_id)


def delete_organization(db: Session, organization_id: int):
    return organization_service.delete_organization(db, organization_id)
