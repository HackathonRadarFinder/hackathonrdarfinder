"""User alerts for saved searches, deadlines and changes (SRS Sec. 7)."""
import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, JSON, String, Uuid, true
from sqlalchemy.sql import func
from app.core.database import Base


class Alert(Base):
    __tablename__ = 'alerts'
    __table_args__ = (Index('ix_alerts_user_id', 'user_id'),)
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey('users.id'), nullable=False)
    kind = Column(String(30), nullable=False)  # saved_search, deadline, change
    query = Column(JSON)
    channel = Column(String(20), nullable=False, server_default='in_app')
    frequency = Column(String(20), nullable=False, server_default='daily')
    enabled = Column(Boolean, nullable=False, server_default=true())
    last_sent_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
