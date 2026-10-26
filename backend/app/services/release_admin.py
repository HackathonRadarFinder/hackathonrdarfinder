"""Administrator reporting and audited role assignment. Never dispatches email."""
import json
import uuid
from fastapi import HTTPException
from sqlalchemy import select, func
from app.models.core import User, Role, AuditLog, Notification
from app.models.email_delivery import EmailDelivery
from app.services.database import database_operation


def assign_role(db, user_id, role_name, actor):
    with database_operation(db):
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(404, 'User not found')
        # Keep an administrator able to manage the service; another admin can
        # change this account after signing in independently.
        if str(user.id) == actor.sub and role_name != 'administrator':
            raise HTTPException(409, 'You cannot remove your own administrator role')
        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            role = Role(name=role_name)
            db.add(role)
        previous = sorted(row.name for row in user.roles)
        user.roles = [role]
        db.add(AuditLog(user_id=uuid.UUID(actor.sub), action='user_role_changed',
            entity_type='user', entity_id=user.id,
            details=json.dumps({'before': previous, 'after': [role_name]})))
        db.commit()
        return {'id': user.id, 'role': role_name}


def audit_history(db, page):
    with database_operation(db):
        rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id)
            .offset((page - 1) * 50).limit(50)).all()
        return {'data': [dict(id=row.id, actor_id=row.user_id, action=row.action,
            entity_type=row.entity_type, entity_id=row.entity_id, details=row.details,
            created_at=row.created_at) for row in rows], 'page': page,
            'total': db.scalar(select(func.count()).select_from(AuditLog))}


def notification_monitor(db):
    with database_operation(db):
        states = dict(db.execute(select(EmailDelivery.status, func.count()).group_by(EmailDelivery.status)).all())
        return {'in_app_total': db.scalar(select(func.count()).select_from(Notification)),
            'in_app_unread': db.scalar(select(func.count()).select_from(Notification).where(Notification.is_read.is_(False))),
            'email_total': sum(states.values()), 'email_by_status': states,
            'dispatch_triggered': False}
