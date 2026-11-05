"""Propose college websites from Wikidata; never trust, crawl, or publish them.

Reads bounded public institution directory pages, searches Wikidata's Action API,
and produces a review artifact. No production DB writes, no scraping college
websites, and no changes to original provenance or collection permissions.

Run: python -m workers.college_website_candidates --out /tmp/college-candidates.json
"""
import argparse
from datetime import datetime, timezone
from difflib import SequenceMatcher
import json
import math
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

DIRECTORY_API = 'https://hackathonrdarfinder.onrender.com/institutions'
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
UA = ('HackathonRadarFinderCollegeSourceBot/1.0 '
      '(https://github.com/HackathonRadarFinder/hackathonrdarfinder)')
TECHNICAL = re.compile(r'engineering|technology|technological|university|polytechnic|computing|'
                       r'computer|technical|science|institute|iit|nit', re.I)


class SourceThrottled(RuntimeError):
    """Stop all further requests when an API signals throttling."""


def normalized(value):
    value = re.sub(r'[^a-z0-9]+', ' ', str(value).casefold()).strip()
    return ' '.join(value.split())


def match_score(college_name, wiki_name):
    a, b = normalized(college_name), normalized(wiki_name)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def safe_website(value):
    """Candidate links are not fetched; restrict even their displayed form."""
    if not isinstance(value, str) or len(value) > 500 or any(ord(c) <= 32 for c in value):
        return None
    try:
        parts = urlsplit(value)
        if (parts.scheme != 'https' or not parts.hostname or parts.username
                or parts.password or parts.port not in (None, 443)
                or parts.fragment or parts.hostname.endswith(('.local', '.internal', '.localhost'))):
            return None
        if parts.hostname == 'localhost' or parts.hostname.replace('.', '').isdigit():
            return None
        return value
    except ValueError:
        return None


def http_json(url, params, *, timeout=45):
    if url not in (DIRECTORY_API, WIKIDATA_API):
        raise ValueError('Only fixed public directory and Wikidata APIs are allowed')
    request = Request(url + '?' + urlencode(params), headers={
        'User-Agent': UA, 'Accept': 'application/json',
    })
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError('Upstream API unavailable')
            if int(response.headers.get('Content-Length', '0') or 0) > 2_000_000:
                raise ValueError('Upstream payload too large')
            data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError('Upstream payload too large')
    except HTTPError as error:
        if error.code in (429, 503):
            # Stop the whole batch, not just this college. This respects the
            # API's throttle window without sleeping past a GitHub job budget.
            raise SourceThrottled('API throttled; no further requests') from None
        raise
    return json.loads(data)


def wikidata_candidates(college, fetch=http_json):
    """Wikidata's P856 provides candidates, not verified official domains."""
    name = ' '.join(str(college.get('name', '')).split())
    name = name.strip(' ').strip(chr(34)).strip(chr(39))
    if len(name) < 7:
        return []
    search = fetch(WIKIDATA_API, {
        'action': 'wbsearchentities', 'search': name[:160],
        'language': 'en', 'type': 'item', 'limit': 4,
        'format': 'json', 'maxlag': 5,
    })
    matches = []
    for hit in search.get('search', [])[:4]:
        if not isinstance(hit, dict):
            continue
        qid, label = hit.get('id'), hit.get('label', '')
        if not re.fullmatch(r'Q[1-9][0-9]*', str(qid or '')):
            continue
        score = match_score(name, label)
        # This threshold is only a triage heuristic; humans must verify the link.
        if score < 0.87:
            continue
        matches.append((qid, label, score))
    if not matches:
        return []
    ids = '|'.join(qid for qid, _, _ in matches)
    entities = fetch(WIKIDATA_API, {
        'action': 'wbgetentities', 'ids': ids, 'props': 'claims',
        'format': 'json', 'maxlag': 5,
    }).get('entities', {})
    found = []
    for qid, label, score in matches:
        claims = entities.get(qid, {}).get('claims', {})
        india = any(
            (row.get('mainsnak', {}).get('datavalue', {}).get('value') or {}).get('id') == 'Q668'
            for row in claims.get('P17', [])
            if isinstance(row.get('mainsnak', {}).get('datavalue', {}).get('value'), dict)
        )
        for claim in claims.get('P856', [])[:4]:
            url = safe_website(claim.get('mainsnak', {}).get('datavalue', {}).get('value'))
            if url:
                found.append({
                    'identifier': college['identifier'], 'college_name': college['name'],
                    'state': college.get('state'), 'district': college.get('district'),
                    'website_candidate': url, 'wikidata_label': label,
                    'wikidata_item': f'https://www.wikidata.org/wiki/{qid}',
                    'country_claim_india': india, 'name_similarity': round(score, 3),
                    'status': 'needs_manual_website_and_terms_review',
                    'event_urls': [],  # No guessed /events paths or unauthorized crawling.
                })
    return found


def run(pages=1, max_colleges=50, start_page=None, fetch=http_json, delay=1.1, sleep=time.sleep):
    first = fetch(DIRECTORY_API, {'page': 1, 'page_size': 100})
    total = int(first['total'])
    page_count = max(1, math.ceil(total / 100))
    start = (datetime.now(timezone.utc).date().toordinal() % page_count) + 1 if start_page is None else start_page
    if not 1 <= start <= page_count:
        raise ValueError('Invalid starting page')
    inspected, errors, candidates, used = 0, 0, [], set()
    throttled = False
    for page_number in range(start, min(start + pages, page_count)):
        listing = first if page_number == 1 else fetch(DIRECTORY_API, {'page': page_number, 'page_size': 100})
        for college in listing.get('data', []):
            if inspected >= max_colleges:
                break
            if not isinstance(college, dict) or not college.get('identifier') or not college.get('name'):
                continue
            # Prioritize institutions more likely to host hackathons, without claiming other colleges do not.
            if not TECHNICAL.search(college['name']) or college.get('website'):
                continue
            inspected += 1
            try:
                matches = wikidata_candidates(college, fetch=fetch)
            except SourceThrottled:
                errors += 1
                throttled = True
                break
            except (HTTPError, URLError, RuntimeError, ValueError, KeyError, TimeoutError):
                errors += 1
                matches = []
            for row in matches:
                key = (row['identifier'], row['website_candidate'])
                if key not in used:
                    used.add(key)
                    candidates.append(row)
            if delay:
                sleep(delay)
        if inspected >= max_colleges or throttled:
            break
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'Wikidata P856 + live public college directory',
        'purpose': 'Review only; no auto-approval, scraping, or database writes',
        'total_colleges': total,
        'start_page': start,
        'colleges_queried': inspected,
        'upstream_errors': errors,
        'rate_limited': throttled,
        'candidates': sorted(candidates, key=lambda row: (-row['name_similarity'], row['college_name'])),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pages', type=int, default=3)
    parser.add_argument('--max-colleges', type=int, default=50)
    parser.add_argument('--start-page', type=int)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    if not 1 <= args.pages <= 5 or not 1 <= args.max_colleges <= 100:
        parser.error('pages must be 1–5 and max-colleges 1–100')
    result = run(pages=args.pages, max_colleges=args.max_colleges, start_page=args.start_page)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('total_colleges','start_page','colleges_queried','upstream_errors')} |
          {'candidates': len(result['candidates']), 'output': str(output)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
