from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.core import Notification
from test_account_integration import journey


def test_stored_notices_are_owned_idempotent_and_read_persists(journey):
    client, (one, two), event_id, engine = journey
    assert client.get('/notifications/').status_code == 401
    for _ in range(2):
        assert client.put(f'/account/saved/{event_id}', headers=one).status_code == 200
    notices = client.get('/notifications/', headers=one).json()['data']
    assert len(notices) == 1 and not notices[0]['is_read']
    assert client.get('/notifications/', headers=two).json()['data'] == []
    path = f"/notifications/{notices[0]['id']}/read"
    assert client.put(path, headers=two).status_code == 404
    assert client.put(path, headers=one).json()['is_read'] is True
    with Session(engine) as db:
        assert db.scalar(select(Notification)).is_read is True
