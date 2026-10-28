from test_events_services import api


def test_validation_errors_do_not_echo_passwords_or_unknown_secret_fields(api):
    password = 'x' * 73
    response = api.client.post('/auth/register', json={'name':'Test','email':'bad',
        'password':password, 'unexpected_secret':'private-marker'})
    assert response.status_code == 422
    assert password not in response.text and 'private-marker' not in response.text
    assert all('input' not in item and 'ctx' not in item for item in response.json()['details'])
