"""Operational run log for every collector (SRS HAC-03, NFR-01, NFR-03)."""
import uuid
from sqlalchemy import Column, DateTime, Index, Integer, String, Text, Uuid
from app.core.database import Base


class IngestRun(Base):
    __tablename__ = 'ingest_runs'
    __table_args__ = (Index('ix_ingest_runs_area_status_finished', 'area', 'status', 'finished_at'),)
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area = Column(String(30), nullable=False)  # hackathons, jobs, investors, colleges
    source = Column(String(100))
    status = Column(String(20), nullable=False)  # running, success, partial, failed
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    items_seen = Column(Integer, nullable=False, server_default='0')
    items_new = Column(Integer, nullable=False, server_default='0')
    items_updated = Column(Integer, nullable=False, server_default='0')
    items_failed = Column(Integer, nullable=False, server_default='0')
    retry_count = Column(Integer, nullable=False, server_default='0')
    error_message = Column(Text)
