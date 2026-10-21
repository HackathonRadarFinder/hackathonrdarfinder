"""Directory facts and unpublished announcements, separate from public events."""
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Uuid
from app.core.database import Base


class Institution(Base):
    __tablename__ = 'institutions'
    id = Column(Integer, primary_key=True)
    identifier = Column(String(120), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(150))
    city = Column(String(150))
    category = Column(String(100), nullable=False)
    website = Column(String(500))
    website_verified_at = Column(DateTime)
    event_urls = Column(JSON, nullable=False, default=list)
    provenance = Column(JSON, nullable=False)
    last_verified_at = Column(DateTime, nullable=False)
    permission_status = Column(String(30), nullable=False, default='awaiting_permission')


class Announcement(Base):
    __tablename__ = 'discovery_announcements'
    __table_args__ = (UniqueConstraint('source_id', 'fingerprint', name='uq_announcement_revision'),)
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(Uuid(as_uuid=True), ForeignKey('sources.id'), nullable=False)
    institution_id = Column(Integer, ForeignKey('institutions.id'), nullable=True)
    fingerprint = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    evidence = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default='pending', index=True)
    observed_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=False)
    reviewed_at = Column(DateTime)
    reviewer_id = Column(Uuid(as_uuid=True), ForeignKey('users.id'))
    review_note = Column(Text)
    hackathon_id = Column(Integer, ForeignKey('hackathons.id'))
