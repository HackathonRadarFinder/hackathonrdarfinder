"""Read-only deployed HTTP checks. No credentials, redirects or local build claims."""
import argparse
import json
import os
import sys
import urllib.request
from urllib.parse import urlsplit


def validate_origin(value):
    if not isinstance(value, str) or any(ord(char) <= 32 or ord(char) == 127 for char in value):
        raise ValueError('Specify a credential-free deployed HTTPS origin')
    parts = urlsplit(value)
    if (parts.scheme != 'https' or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.query or parts.fragment or parts.path not in ('', '/')):
        raise ValueError('Specify a credential-free deployed HTTPS origin')
    if parts.port not in (None, 443):
        raise ValueError('Specify the deployed HTTPS origin on port 443')
    return value.rstrip('/')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirected smoke request refused')


def verify(origin, opener=None):
    origin = validate_origin(origin)
    opener = opener or urllib.request.build_opener(NoRedirect())
    for path in ('/health', '/api/health', '/api/events/?page=1&page_size=1', '/'):
        request = urllib.request.Request(origin + path, headers={'Accept': 'application/json' if path.startswith('/api/') else '*/*'})
        with opener.open(request, timeout=15) as response:
            if response.status != 200:
                raise ValueError('Smoke endpoint did not return HTTP 200')
            body = response.read(1_000_001)
            if len(body) > 1_000_000:
                raise ValueError('Smoke response exceeds limit')
        if path == '/health':
            if body.strip() != b'ok':
                raise ValueError('Frontend health check failed')
        elif path == '/api/health':
            if json.loads(body).get('status') != 'healthy':
                raise ValueError('Backend health check failed')
        elif path.startswith('/api/events/'):
            data = json.loads(body)
            if (not isinstance(data.get('data'), list) or type(data.get('total')) is not int
                    or data['total'] < 0 or data.get('page') != 1 or data.get('page_size') != 1):
                raise ValueError('Database-backed catalog check failed')
        elif b'id="root"' not in body and b"id='root'" not in body:
            raise ValueError('Frontend application shell missing')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        origin = validate_origin(os.environ.get('VERIFY_BASE_URL'))
        if not args.validate_only:
            verify(origin)
            print('Deployed HTTP liveness, database catalog and frontend shell checks passed.')
        return 0
    except Exception:
        # Do not log connection details, response data, credentials or full URLs.
        print('Post-rollback verification failed; investigate the approved environment.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
