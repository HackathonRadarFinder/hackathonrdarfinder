"""Durable discovery policy, runs, identities and evidence; no network on import."""
import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, Uuid
from app.core.database import Base


class DiscoverySource(Base):
    __tablename__ = 'discovery_sources'
    source_id = Column(Uuid(as_uuid=True), ForeignKey('sources.id'), primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    config = Column(JSON, nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    interval_seconds = Column(Integer, nullable=False, default=21600)
    next_run_at = Column(DateTime, nullable=False)


class DiscoveryRun(Base):
    __tablename__ = 'discovery_runs'
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(Uuid(as_uuid=True), ForeignKey('sources.id'), nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    status = Column(String(32), nullable=False)
    error_code = Column(String(64))
    metrics = Column(JSON, nullable=False, default=dict)


class DiscoveryLock(Base):
    __tablename__ = 'discovery_lock'
    id = Column(Integer, primary_key=True)
    run_id = Column(Uuid(as_uuid=True), ForeignKey('discovery_runs.id'), nullable=False)


class DiscoveryEvent(Base):
    __tablename__ = 'discovery_events'
    __table_args__ = (UniqueConstraint('source_id', 'canonical_url', name='uq_discovery_identity'),)
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(Uuid(as_uuid=True), ForeignKey('sources.id'), nullable=False)
    canonical_url = Column(String(500), nullable=False)
    hackathon_id = Column(Integer, ForeignKey('hackathons.id'), nullable=False)
    last_observed_at = Column(DateTime, nullable=False)


class DiscoveryEvidence(Base):
    __tablename__ = 'discovery_evidence'
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Integer, ForeignKey('hackathons.id'), nullable=False)
    run_id = Column(Uuid(as_uuid=True), ForeignKey('discovery_runs.id'), nullable=False)
    source_id = Column(Uuid(as_uuid=True), ForeignKey('sources.id'), nullable=False)
    observed_at = Column(DateTime, nullable=False)
    checksum = Column(String(64), nullable=False)
    document_url = Column(String(500), nullable=False)
    adapter_version = Column(String(64), nullable=False)
    snapshot = Column(JSON, nullable=False)
