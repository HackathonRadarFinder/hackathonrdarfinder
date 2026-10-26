"""Explicit Brabble API refresh to an immutable review snapshot. No database writes."""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ENDPOINT = 'https://brabble.ai/api/listings'
MAX_REQUESTS = 20  # Includes retries; hourly scheduling is <=480 requests/day.


def collect_api(output, key, *, session=None, sleep=time.sleep):
    if not key or not key.strip():
        raise ValueError('Set BRABBLE_API_KEY in the server secret environment')
    if output.exists():
        raise ValueError('Use a new snapshot directory; existing evidence is never overwritten')
    session = session or requests.Session()
    attempts = 0
    exports, envelopes, platforms = [], [], {}
    try:
        for platform in ('unstop', 'devfolio'):
            listings, offset = [], 0
            while True:
                for retry in range(3):
                    if attempts >= MAX_REQUESTS:
                        raise ValueError('Per-run API request budget exhausted; no snapshot published')
                    if attempts:
                        sleep(max(1, 2 ** retry))
                    attempts += 1
                    try:
                        response = session.get(ENDPOINT, params={'hub': 'hackathons', 'platform': platform,
                                               'limit': 200, 'offset': offset},
                                               headers={'Authorization': 'Bearer ' + key, 'Accept': 'application/json'},
                                               timeout=(5, 20), allow_redirects=False, stream=True)
                    except requests.RequestException:
                        if retry == 2:
                            raise ValueError('API transport failed; no snapshot published') from None
                        continue
                    try:
                        if response.status_code >= 500 and retry < 2:
                            continue
                        if response.status_code != 200:
                            raise ValueError(f'API HTTP {response.status_code}; stop without bypass')
                        if 'json' not in response.headers.get('Content-Type', '').lower():
                            raise ValueError('Expected API JSON')
                        body = bytearray()
                        for chunk in response.iter_content(16384):
                            body.extend(chunk)
                            if len(body) > 5_000_000:
                                raise ValueError('API response exceeded 5 MB')
                        page = json.loads(body.decode('utf-8-sig'))
                        remaining = response.headers.get('x-ratelimit-remaining')
                        remaining = int(remaining) if remaining is not None else None
                    finally:
                        response.close()
                    break
                else:
                    raise ValueError('API retries exhausted')
                rows = page.get('listings')
                if (not isinstance(rows, list) or page.get('count') != len(rows)
                        or page.get('offset') != offset or not isinstance(page.get('total'), int)
                        or page['total'] < offset + len(rows)):
                    raise ValueError('Invalid API pagination envelope')
                acquired = datetime.now(timezone.utc).isoformat()
                for raw in rows:
                    if raw.get('platform', '').lower() != platform:
                        raise ValueError('API returned an unexpected platform')
                    prize = raw.get('prize') or {}
                    exports.append({'title': raw.get('title'), 'organization': raw.get('organiser'),
                                    'source': raw.get('platform'), 'url': raw.get('url'),
                                    'provider': 'Brabble.ai', 'provider_id': raw.get('id'),
                                    'provider_url': raw.get('shareUrl'), 'kind': raw.get('kind'),
                                    'type': raw.get('type'), 'location': raw.get('city'), 'mode': raw.get('mode'),
                                    'prize': prize.get('label'), 'acquired_at': acquired,
                                    'source_refreshed_at': page.get('refreshedAt'),
                                    'review_status': 'needs_review'})
                listings.extend(rows)
                envelopes.append({'platform': platform, 'acquired_at': acquired, 'response': page})
                offset += len(rows)
                if offset >= page['total']:
                    break
                if not rows or (remaining is not None and remaining <= 1):
                    raise ValueError('Pagination incomplete or API quota low; stop until next authorized run')
            platforms[platform] = listings
            # Respect a shared key's remaining daily budget before the second platform.
            if platform == 'unstop' and remaining is not None and remaining <= 1:
                raise ValueError('API quota low; no complete snapshot published')
    finally:
        session.close()
    output.mkdir(parents=True, exist_ok=False)
    for platform, rows in platforms.items():
        (output / f'{platform}.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'response_envelopes.json').write_text(json.dumps(envelopes, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'hackathons.json').write_text(json.dumps(exports, ensure_ascii=False, indent=2), encoding='utf-8')
    with (output / 'hackathons.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(exports[0]) if exports else ['provider_id'])
        writer.writeheader()
        writer.writerows(exports)
    return {'records': len(exports), 'requests': attempts, 'database_writes': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect', action='store_true', help='Explicitly perform authorized API requests')
    parser.add_argument('--out', type=Path, default=Path('radar_collector/output/brabble-snapshots') /
                        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    args = parser.parse_args()
    if not args.collect:
        print(json.dumps({'network_requests': 0, 'endpoint': ENDPOINT, 'max_requests_per_run': MAX_REQUESTS,
                          'output': str(args.out), 'database_writes': False}))
        return 0
    try:
        print(json.dumps(collect_api(args.out, os.environ.get('BRABBLE_API_KEY', ''))))
        return 0
    except (ValueError, OSError, requests.RequestException):
        # Never print request objects, headers, secret values or provider response bodies.
        print('API refresh failed; check authorization, quota, response schema and output directory. No database writes.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
