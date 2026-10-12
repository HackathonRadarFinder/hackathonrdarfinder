"""Email transport state, separate from existing in-app notifications."""
import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, Index
from app.core.database import Base


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"
    __table_args__ = (
        UniqueConstraint("user_id", "hackathon_id", "kind", "event_at", name="uq_email_reminder"),
        Index("ix_email_delivery_due", "status", "next_attempt_at"),
        CheckConstraint("kind IN ('registration', 'upcoming')", name="ck_email_kind"),
        CheckConstraint("status IN ('pending', 'sending', 'retry', 'accepted', 'failed', 'cancelled', 'unknown')", name="ck_email_status"),
        CheckConstraint("attempts >= 0 AND attempts <= 3", name="ck_email_attempts"),
    )
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    hackathon_id = Column(Integer, ForeignKey("hackathons.id"), nullable=False)
    kind = Column(String(32), nullable=False)
    # UTC-naive storage matches existing Hackathon datetime columns.
    event_at = Column(DateTime, nullable=False)
    next_attempt_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    claimed_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    error_code = Column(String(40), nullable=True)
