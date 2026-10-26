"""API refresh transport contracts with mocked responses only; no real API key."""
import json
import pytest
from workers.refresh_brabble import collect_api, ENDPOINT


class Response:
    def __init__(self, page=None, status=200, remaining=500):
        self.status_code = status
        self.headers = {'Content-Type': 'application/json', 'x-ratelimit-remaining': str(remaining)}
        self.page = page
        self.closed = False

    def iter_content(self, size):
        yield json.dumps(self.page).encode()

    def close(self):
        self.closed = True


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.closed = False

    def get(self, url, **options):
        assert url == ENDPOINT
        assert options['allow_redirects'] is False
        assert options['headers']['Authorization'] == 'Bearer test-key-never-a-real-secret'
        self.requests.append(options)
        return next(self.responses)

    def close(self):
        self.closed = True


def page(platform, *, total=1, offset=0):
    return {'refreshedAt': '2026-10-25T17:00:00Z', 'origin': 'store', 'attribution': 'Credit Brabble.ai',
            'count': 1, 'total': total, 'offset': offset, 'listings': [
                {'id': f'{platform}-{offset}', 'platform': platform.title(), 'title': 'Test', 'prize': {}}]}


def test_refresh_paginates_and_retains_envelopes_without_secret(tmp_path):
    target = tmp_path / 'new-snapshot'
    responses = [Response(page('unstop', total=2)), Response(page('unstop', total=2, offset=1)),
                 Response(page('devfolio'))]
    session = Session(responses)
    delays = []
    result = collect_api(target, 'test-key-never-a-real-secret', session=session, sleep=delays.append)
    assert result == {'records': 3, 'requests': 3, 'database_writes': False}
    assert delays == [1, 1]
    assert session.requests[1]['params']['offset'] == 1
    assert session.closed and all(response.closed for response in responses)
    assert len(json.loads((target / 'response_envelopes.json').read_text())) == 3
    assert all('test-key-never-a-real-secret' not in file.read_text(encoding='utf-8-sig')
               for file in target.iterdir())


@pytest.mark.parametrize('status', [301, 401, 403, 429])
def test_access_or_quota_denial_stops_without_publishing(tmp_path, status):
    session = Session([Response(status=status)])
    target = tmp_path / 'not-published'
    with pytest.raises(ValueError, match='stop without bypass'):
        collect_api(target, 'test-key-never-a-real-secret', session=session, sleep=lambda _: None)
    assert len(session.requests) == 1 and session.closed
    assert not target.exists()


def test_low_quota_stops_and_retries_are_bounded(tmp_path):
    target = tmp_path / 'not-published'
    session = Session([Response(page('unstop', total=2), remaining=1)])
    with pytest.raises(ValueError, match='quota low'):
        collect_api(target, 'test-key-never-a-real-secret', session=session, sleep=lambda _: None)
    assert not target.exists()
    session = Session([Response(status=503), Response(status=503), Response(status=503)])
    with pytest.raises(ValueError):
        collect_api(target, 'test-key-never-a-real-secret', session=session, sleep=lambda _: None)
    assert len(session.requests) == 3 and not target.exists()


def test_existing_snapshot_and_missing_key_do_not_fetch(tmp_path):
    session = Session([])
    with pytest.raises(ValueError, match='BRABBLE_API_KEY'):
        collect_api(tmp_path / 'missing', '', session=session)
    with pytest.raises(ValueError, match='never overwritten'):
        collect_api(tmp_path, 'test-key-never-a-real-secret', session=session)
    assert not session.requests
