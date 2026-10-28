"""Explicit local-only live journey. Creates one smoke account, no fake events/email.

Run only against this release's Compose Nginx port 5175. Credentials stay in memory.
The account, its genuine saved event and read notice remain for persistence evidence.
"""
import json
import secrets
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:5175/api"


def run():
    token = None
    def call(path, method="GET", body=None, status=200):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(BASE + path, method=method, headers=headers,
            data=json.dumps(body).encode() if body is not None else None)
        try:
            response = urllib.request.urlopen(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        assert response.status == status, f"{method} {path}: unexpected status {response.status}"
        return json.load(response)
    assert call('/health')['status'] == 'healthy'
    events = call('/events/?page=1&page_size=2')
    assert events['total'] > 0 and events['data']
    event = events['data'][0]
    assert call(f"/events/{event['id']}")['data']['id'] == event['id']
    assert call('/events/?page=1&q=HackHarvard')['total'] > 0
    assert call('/events/?page=1&location=Hyderabad&mode=In-Person')['total'] > 0
    call('/account/saved', status=401)
    email = f"mvp-smoke-{secrets.token_hex(6)}@example.com"
    password = secrets.token_urlsafe(24)
    call('/auth/register', 'POST', {'name':'Local MVP smoke account', 'email':email, 'password':password}, 201)
    token = call('/auth/login', 'POST', {'email':email,'password':password})['access_token']
    assert call('/auth/me')['role'] == 'user'
    call('/admin/stats', status=403)
    call(f"/account/saved/{event['id']}", 'PUT')
    call(f"/account/saved/{event['id']}", 'PUT')
    assert len(call('/account/saved')['data']) == 1
    values = {'email_reminders':True,'email_registration_reminders':True,'email_upcoming_reminders':False}
    assert call('/account/preferences','PUT',values) == values
    assert call('/account/preferences') == values
    values['email_reminders'] = False
    call('/account/preferences','PUT',values)
    notices = call('/notifications/')['data']
    assert len(notices) == 1
    call(f"/notifications/{notices[0]['id']}/read", 'PUT')
    call(f"/account/saved/{event['id']}", 'DELETE')
    assert call('/account/saved')['data'] == []
    call(f"/account/saved/{event['id']}", 'PUT')
    for notice in call('/notifications/')['data']:
        call(f"/notifications/{notice['id']}/read", 'PUT')
    call('/auth/logout', 'POST')
    call('/auth/me', status=401)
    token = call('/auth/login', 'POST', {'email':email,'password':password})['access_token']
    assert len(call('/account/saved')['data']) == 1
    assert call('/notifications/')['data'][0]['is_read']
    assert not call('/account/preferences')['email_reminders']
    forecasts = call('/predictions/catalog')['data']
    assert forecasts == []  # uncalibrated baseline is internal evaluation only
    call('/auth/logout', 'POST')
    print(json.dumps({'live_journey':'PASS','genuine_events':events['total'],
                     'organizations_with_predictions':len(forecasts),'email_sent':False}))


if __name__ == '__main__':
    try:
        run()
    except Exception:
        raise SystemExit('Local MVP smoke failed; credentials and response bodies suppressed.')
