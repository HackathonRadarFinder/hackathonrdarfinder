"""Jobs and internships (SRS JOB-01..JOB-03)."""
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.sql import func
from app.core.database import Base


class Employer(Base):
    __tablename__ = 'employers'
    __table_args__ = (UniqueConstraint('normalized_name', name='uq_employers_normalized_name'),)
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    website = Column(String(500))
    country = Column(String(100))
    source_url = Column(String(500))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class Job(Base):
    __tablename__ = 'jobs'
    __table_args__ = (
        UniqueConstraint('source', 'external_id', name='uq_jobs_source_external_id'),
        Index('ix_jobs_employer_id', 'employer_id'),
        Index('ix_jobs_canonical_url', 'canonical_url'),
        Index('ix_jobs_active_window', 'archived_at', 'first_published_at'),
        Index('ix_jobs_type_country', 'job_type', 'country', 'first_published_at'),
    )
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employer_id = Column(Uuid(as_uuid=True), ForeignKey('employers.id'), nullable=False)
    title = Column(String(255), nullable=False)
    job_type = Column(String(30), nullable=False)  # job, internship, apprenticeship
    seniority = Column(String(30))  # entry, mid, senior (senior-only is excluded from fresher views)
    country = Column(String(100))
    city = Column(String(150))
    location_text = Column(String(255))
    remote_mode = Column(String(20))  # remote, hybrid, onsite
    compensation_text = Column(String(255))  # only when published by the source
    skills = Column(JSON)
    eligibility = Column(Text)
    experience_min_years = Column(Integer)
    experience_max_years = Column(Integer)
    apply_url = Column(String(500), nullable=False)
    canonical_url = Column(String(500))
    source = Column(String(100), nullable=False)
    source_url = Column(String(500))
    external_id = Column(String(150))  # requisition / source job id
    posted_at = Column(DateTime)
    first_published_at = Column(DateTime, nullable=False)
    closes_at = Column(DateTime)
    first_seen_at = Column(DateTime, nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime, nullable=False, server_default=func.now())
    last_checked_at = Column(DateTime, nullable=False, server_default=func.now())
    archived_at = Column(DateTime)
