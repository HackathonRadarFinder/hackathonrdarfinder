"""Protected registry controls; public event history has no operational secrets."""
from datetime import datetime, timezone
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_source_manager
from app.core.database import get_db
from app.models.core import Source, EventVersion, AuditLog
from app.models.discovery import DiscoverySource, DiscoveryRun, DiscoveryEvidence
from app.schemas.discovery import SourcePolicy
from app.schemas.responses import DatabaseId
from app.services.database import database_operation
from app.services.discovery_service import register_source
from app.services.event_service import get_event

router = APIRouter(tags=['Discovery'])


@router.get('/admin/discovery/sources', dependencies=[Depends(require_source_manager)])
def sources(db: Session = Depends(get_db)):
    with database_operation(db):
        rows = db.scalars(select(DiscoverySource).order_by(DiscoverySource.key)).all()
        return {'data': [{'key': row.key, 'source_id': row.source_id, 'config': row.config,
            'enabled': row.enabled, 'interval_seconds': row.interval_seconds,
            'next_run_at': row.next_run_at} for row in rows]}


@router.put('/admin/discovery/sources')
def configure_source(body: SourcePolicy, actor=Depends(require_source_manager), db: Session = Depends(get_db)):
    with database_operation(db):
        try:
            row = register_source(db, body, datetime.now(timezone.utc), commit=False)
        except ValueError:
            db.rollback()
            raise HTTPException(422, 'Source must match a verified institution event URL') from None
        db.add(AuditLog(user_id=uuid.UUID(actor.sub), action='discovery_source_configured',
            entity_type='source', entity_id=row.source_id,
            details=json.dumps(body.model_dump(mode='json'))))
        db.commit()
        return {'key': row.key, 'enabled': row.enabled, 'network_started': False}


@router.get('/admin/discovery/runs', dependencies=[Depends(require_source_manager)])
def runs(db: Session = Depends(get_db)):
    with database_operation(db):
        rows = db.execute(select(DiscoveryRun, DiscoverySource.key).join(DiscoverySource,
            DiscoverySource.source_id == DiscoveryRun.source_id)
            .order_by(DiscoveryRun.started_at.desc(), DiscoveryRun.id).limit(100)).all()
        return {'data': [{'id': row.id, 'source_id': row.source_id, 'source_key': key, 'status': row.status,
            'started_at': row.started_at, 'finished_at': row.finished_at,
            'error_code': row.error_code, 'metrics': row.metrics} for row, key in rows]}


@router.get('/events/{event_id}/discovery')
def event_discovery(event_id: DatabaseId, db: Session = Depends(get_db)):
    get_event(db, event_id)
    with database_operation(db):
        evidence = db.execute(select(DiscoveryEvidence, Source.name).join(Source,
            DiscoveryEvidence.source_id == Source.id).where(DiscoveryEvidence.hackathon_id == event_id)
            .order_by(DiscoveryEvidence.observed_at.desc(), DiscoveryEvidence.id).limit(20)).all()
        versions = db.scalars(select(EventVersion).where(EventVersion.hackathon_id == event_id,
            EventVersion.snapshot.is_not(None)).order_by(EventVersion.version_number.desc()).limit(20)).all()
        return {'data': {'evidence': [{'source': name, 'document_url': row.document_url,
            'observed_at': row.observed_at, 'checksum': row.checksum,
            'adapter_version': row.adapter_version} for row, name in evidence],
            'versions': [{'version': row.version_number, 'observed_at': row.created_at,
                'snapshot': row.snapshot, 'changed_fields': (row.changes or {}).get('fields', [])}
                for row in versions if isinstance(row.snapshot, dict)]}}
