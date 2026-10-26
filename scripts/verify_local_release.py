"""Verify local Compose upgrade/restart without resetting data or exposing credentials."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.test-support/release-final/local-stack.json'
CODE = """import hashlib,json
from sqlalchemy import text
from app.core.database import engine
with engine.connect() as c:
 result={'revision':c.execute(text('select version_num from alembic_version')).scalar(),'tables':{}}
 for table in ['hackathons','users','saved_items','institutions']:
  ids=sorted(str(x) for x in c.scalars(text('select id from '+table)))
  result['tables'][table]={'count':len(ids),'identity_sha256':hashlib.sha256(json.dumps(ids).encode()).hexdigest()}
 print(json.dumps(result))
"""
def state():
    return json.loads(subprocess.check_output(['docker','exec','hackathon-radar-backend','python','-c',CODE],text=True))
def ready():
    for _ in range(90):
        try:
            with urlopen('http://127.0.0.1:5173/api/ready',timeout=3) as response:
                if response.status==200:return
        except OSError:pass
        time.sleep(1)
    raise RuntimeError('Local proxy readiness did not recover')
def main():
    before=state()
    subprocess.run(['docker','compose','-p','hackathonradarfinder','up','-d','--no-build'],cwd=ROOT,check=True)
    ready()
    upgraded=state()
    assert upgraded==before, 'Data identity changed during application upgrade'
    subprocess.run(['docker','compose','-p','hackathonradarfinder','restart','db','backend','frontend'],cwd=ROOT,check=True)
    ready()
    after=state()
    assert after==before, 'Data identity changed during restart'
    checks={}
    for path in ['/api/health','/api/ready','/api/auth/status','/api/events/?page=1&page_size=5','/api/institutions?page_size=1','/api/predictions/readiness']:
        with urlopen('http://127.0.0.1:5173'+path,timeout=10) as response:
            checks[path]=response.status
    OUT.parent.mkdir(parents=True,exist_ok=True)
    report={'before':before,'after':after,'identity_preserved':True,'proxy_checks':checks,'database_volumes_deleted':False}
    OUT.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
