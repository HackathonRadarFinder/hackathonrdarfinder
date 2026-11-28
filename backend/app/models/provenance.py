"""Source provenance, aliases and conflicting claims shared by investors, funds and startups (SRS INV-03)."""
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.sql import func
from app.core.database import Base


class SourceEvidence(Base):
    __tablename__ = 'source_evidence'
    __table_args__ = (Index('ix_source_evidence_source_url', 'source_url'),)
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(String(500), nullable=False)
    source_name = Column(String(150))
    verification_method = Column(String(100))
    verified_at = Column(DateTime)
    observed_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class EntityAlias(Base):
    __tablename__ = 'entity_aliases'
    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', 'alias_normalized', name='uq_entity_alias'),
        Index('ix_entity_aliases_alias_normalized', 'alias_normalized'),
    )
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(20), nullable=False)  # investor, fund or startup
    entity_id = Column(Integer, nullable=False)  # id in investors, funds or startups, chosen by entity_type
    alias = Column(String(255), nullable=False)
    alias_normalized = Column(String(255), nullable=False)
    verification_status = Column(String(20), nullable=False, server_default='unverified')  # unverified, verified, disputed
    first_seen_at = Column(DateTime, nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime, nullable=False, server_default=func.now())


class EntityAliasSource(Base):
    """Links an alias to every source that supports it (many-to-many)."""
    __tablename__ = 'entity_alias_sources'
    __table_args__ = (Index('ix_entity_alias_sources_source_evidence_id', 'source_evidence_id'),)
    alias_id = Column(Uuid(as_uuid=True), ForeignKey('entity_aliases.id', ondelete='CASCADE'), primary_key=True)
    source_evidence_id = Column(Uuid(as_uuid=True), ForeignKey('source_evidence.id'), primary_key=True)


class EntityClaim(Base):
    __tablename__ = 'entity_claims'
    __table_args__ = (Index('ix_entity_claims_entity', 'entity_type', 'entity_id', 'field_name'),)
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(20), nullable=False)
    entity_id = Column(Integer, nullable=False)  # id in investors, funds or startups, chosen by entity_type
    field_name = Column(String(100), nullable=False)
    value = Column(Text)
    source_evidence_id = Column(Uuid(as_uuid=True), ForeignKey('source_evidence.id'), nullable=False)
    observed_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False)  # latest_confirmed, conflicting, superseded
