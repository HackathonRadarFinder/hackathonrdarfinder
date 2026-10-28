from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_db_user
from app.core.database import get_db
from app.models.core import Notification
from app.schemas.notification import NotificationResponse
from app.schemas.responses import DataResponse
from app.services.database import database_operation

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)


@router.get("/", response_model=DataResponse[list[NotificationResponse]])
def get_notifications(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    with database_operation(db):
        rows = db.scalars(select(Notification).where(Notification.user_id == user.id)
                          .order_by(Notification.created_at.desc(), Notification.id).limit(100)).all()
        return {"message": "Latest account notifications", "data": rows}


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: UUID, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    with database_operation(db):
        row = db.scalar(select(Notification).where(Notification.id == notification_id,
                                                   Notification.user_id == user.id))
        if row is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        row.is_read = True
        db.commit()
        db.refresh(row)
        return row
