from pathlib import Path
import os, sys, tempfile, subprocess
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'backend'))
temporary = tempfile.TemporaryDirectory(prefix='radar-disposable-')
os.environ.update(DATABASE_URL=f"sqlite:///{Path(temporary.name).as_posix()}/fixture.db", SECRET_KEY='disposable-frontend-test-secret-key-123456789', DEBUG='false', EMAIL_MODE='disabled')
subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=root / 'backend', env=os.environ, check=True)
from app.main import app
from app.core.database import engine, SessionLocal
from app.models.core import User, Role
from app.models.organization import Organization
from app.models.hackathon import Hackathon
import bcrypt
# Schema is created by the existing Alembic migration chain.
with SessionLocal() as db:
    if not db.query(User).first():
        db.add_all([User(name='Disposable Admin', email='admin@example.com', password_hash=bcrypt.hashpw(b'DisposablePassword123!', bcrypt.gensalt()).decode(), roles=[Role(name='administrator')]), User(name='Disposable User', email='user@example.com', password_hash=bcrypt.hashpw(b'DisposablePassword123!', bcrypt.gensalt()).decode(), roles=[Role(name='user')])])
        org = Organization(name='Google Developer Test Group')
        db.add(org)
        db.flush()
        for i in range(25):
            db.add(Hackathon(title=f'Disposable Event {i+1}', organization_id=org.id, description='Synthetic data for local integration verification only.', mode='Online' if i % 2 == 0 else 'Hybrid', location='Delhi' if i < 20 else 'Mumbai', url='https://example.com/event'))
        db.commit()
if __name__ == '__main__':
    import uvicorn
    try:
        uvicorn.run(app, host='127.0.0.1', port=8020, log_level='warning')
    finally:
        engine.dispose()
        temporary.cleanup()
