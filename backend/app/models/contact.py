"""Public professional contacts with field-level provenance (SRS HAC-02, NFR-09). Exactly one owner per row."""
import uuid
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Uuid
from sqlalchemy.sql import func
from app.core.database import Base


class Contact(Base):
    __tablename__ = 'contacts'
    __table_args__ = (
        CheckConstraint(
            '(CASE WHEN hackathon_id IS NULL THEN 0 ELSE 1 END + CASE WHEN employer_id IS NULL THEN 0 ELSE 1 END'
            ' + CASE WHEN investor_id IS NULL THEN 0 ELSE 1 END + CASE WHEN fund_id IS NULL THEN 0 ELSE 1 END) = 1',
            name='ck_contact_single_owner'),
        Index('ix_contacts_hackathon_id', 'hackathon_id'),
    )
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Integer, ForeignKey('hackathons.id'))
    employer_id = Column(Uuid(as_uuid=True), ForeignKey('employers.id'))
    investor_id = Column(Integer, ForeignKey('investors.id'))
    fund_id = Column(Integer, ForeignKey('funds.id'))
    name = Column(String(255))
    designation = Column(String(255))
    email = Column(String(320))  # public business email only
    phone = Column(String(50))
    field_provenance = Column(JSON)  # per-field source URL and verified time
    visibility = Column(String(20), nullable=False, server_default='public')
    source_evidence_id = Column(Uuid(as_uuid=True), ForeignKey('source_evidence.id'))
    verified_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
