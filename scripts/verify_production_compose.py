"""Test the production Compose topology in a uniquely owned disposable project.

Never uses development volumes, .env or configured source credentials.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import uuid
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    run_id = uuid.uuid4().hex[:12]
    project = 'radar-acceptance-' + run_id
    output = ROOT / '.test-support' / project
    output.mkdir(parents=True)
    env_file = output / '.env'
    password = secrets.token_hex(24)
    env_file.write_text(f'POSTGRES_USER=acceptance\nPOSTGRES_DB=radar_acceptance_{run_id}\nPOSTGRES_PASSWORD={password}\n'
        f'DATABASE_URL=postgresql+psycopg://acceptance:{password}@db:5432/radar_acceptance_{run_id}\n'
        f'SECRET_KEY={secrets.token_hex(32)}\nDEBUG=false\nEMAIL_MODE=disabled\n', encoding='utf-8')
    env = dict(os.environ, PRODUCTION_ENV_FILE=str(env_file), HTTP_PORT='0',
        BACKEND_IMAGE=os.environ.get('ACCEPTANCE_BACKEND_IMAGE', 'hackathonradarfinder-backend:automation'), FRONTEND_IMAGE=os.environ.get('ACCEPTANCE_FRONTEND_IMAGE', 'hackathonradarfinder-frontend:automation'),
        POSTGRES_USER='acceptance', POSTGRES_DB='radar_acceptance_' + run_id, POSTGRES_PASSWORD=password)
    from validate_production_compose import validate
    validate(env_file)
    prefix = ['docker', 'compose', '-p', project, '--env-file', str(env_file), '-f', str(ROOT / 'docker-compose.production.yml')]
    def compose(*args):
        result = subprocess.run([*prefix, *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=360)
        if result.returncode:
            raise RuntimeError('Owned Compose operation failed: ' + args[0])
        return result.stdout.strip()
    def code(value):
        return compose('exec', '-T', 'backend', 'python', '-c', value)
    def scalar(sql):
        return int(code('from sqlalchemy import text; from app.core.database import engine; '
            f'\nwith engine.connect() as c: print(c.scalar(text({sql!r})))'))
    report = {'project': project, 'existing_development_writes': False, 'smtp_enabled': False}
    try:
        compose('up', '-d', '--wait', '--wait-timeout', '240')
        port = int(compose('port', 'frontend', '8080').rsplit(':', 1)[1])
        with urlopen(f'http://127.0.0.1:{port}/api/ready') as response:
            assert response.status == 200
        assert scalar('select count(*) from hackathons') == 0
        code('from datetime import datetime,timezone; from sqlalchemy import text; from app.core.database import engine,SessionLocal; '
            'from app.services.discovery_service import run_source,DISCOVERY_ADVISORY_LOCK; '
            '\nwith engine.connect().execution_options(isolation_level="AUTOCOMMIT") as guard:\n guard.execute(text("SELECT pg_advisory_lock(:key)"),{"key":DISCOVERY_ADVISORY_LOCK})\n try:\n  with SessionLocal() as db: assert run_source(db,None,datetime.now(timezone.utc))["status"]=="busy"\n finally: guard.execute(text("SELECT pg_advisory_unlock(:key)"),{"key":DISCOVERY_ADVISORY_LOCK})')
        report['overlap_prevented'] = True
        # Existing explicitly reviewed offline manifest exercises scheduling only;
        # this is not a live acquisition or new human review claim.
        code('from datetime import datetime,timezone; from app.core.database import SessionLocal; '
            'from app.services.discovery_service import register_source,curated_policy; '
            '\nwith SessionLocal() as db: register_source(db,curated_policy(datetime.now(timezone.utc),enabled=True),datetime.now(timezone.utc))')
        for _ in range(40):
            if scalar('select count(*) from hackathons') == 5:
                break
            time.sleep(2)
        assert scalar('select count(*) from hackathons') == 5
        # Crash simulation: an abandoned durable marker with an alive-independent
        # next-run timestamp must recover after restart, without waiting six hours.
        compose('stop', 'collector')
        code('from datetime import datetime,timedelta,timezone; import uuid; from sqlalchemy import select; '
            'from app.core.database import SessionLocal; from app.models.discovery import DiscoverySource,DiscoveryRun,DiscoveryLock; '
            '\nwith SessionLocal.begin() as db:\n s=db.scalar(select(DiscoverySource)); '
            "r=DiscoveryRun(id=uuid.uuid4(),source_id=s.source_id,started_at=datetime.now(timezone.utc).replace(tzinfo=None),status='running',metrics={}); "
            'db.add(r);db.flush();db.add(DiscoveryLock(id=1,run_id=r.id));s.next_run_at=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(hours=6)')
        compose('start', 'collector')
        for _ in range(40):
            if scalar("select count(*) from discovery_runs where status='interrupted'") == 1:
                break
            time.sleep(2)
        assert scalar("select count(*) from discovery_runs where status='interrupted'") == 1
        assert scalar('select count(*) from hackathons') == 5
        compose('restart', 'db', 'backend', 'frontend', 'collector')
        compose('up', '-d', '--wait', '--wait-timeout', '240')
        assert scalar('select count(*) from hackathons') == 5
        report.update(status='passed', collector_scheduled=True, interrupted_run_recovered=True,
            restart_persistence=True, records_in_owned_stack=5, public_deployment=False)
        # pg_dump creates a private backup in this project's own backup volume.
        compose('--profile', 'tools', 'run', '--rm', 'backup', 'pg_dump', '--format=custom', '--file=/backups/acceptance.dump')
        restored = compose('--profile', 'tools', 'run', '--rm', 'backup', 'sh', '-c', 'createdb radar_restore_verify && pg_restore --exit-on-error --single-transaction --dbname=radar_restore_verify /backups/acceptance.dump && psql --dbname=radar_restore_verify --tuples-only --no-align --command="select count(*) from hackathons"')
        assert restored.strip() == '5'
        report['backup_restored_to_owned_database'] = True
        report['backup_created'] = True
        print(json.dumps(report), flush=True)
    finally:
        # Verify exact generated project prefix; these are never existing volumes.
        assert project == 'radar-acceptance-' + run_id and len(run_id) == 12
        compose('down', '--volumes', '--remove-orphans')
        env_file.unlink(missing_ok=True)
    (ROOT / '.test-support/production-compose-report.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
