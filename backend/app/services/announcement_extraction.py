"""Bounded deterministic extraction. All results require review before publication.

Never infer dates from URL/year or turn sitemap links into confirmed events.
No scripts execute; text-only fallbacks remain incomplete candidates.
"""
from datetime import datetime
from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from defusedxml import ElementTree
from app.schemas.institution import public_https

KEYWORD = re.compile(r'\b(?:hack(?:athon|fest|[- ]a[- ]thon|\d+)|megathon)\b', re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scripts, self.text, self.links = [], [], []
        self.ld, self.ignore, self.current = False, False, []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style'):
            self.ignore = True
            self.ld = tag == 'script' and attrs.get('type', '').lower() == 'application/ld+json'
            self.current = []
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            if self.ld:
                self.scripts.append(''.join(self.current))
            self.ignore, self.ld = False, False

    def handle_data(self, data):
        if self.ld:
            self.current.append(data)
        elif not self.ignore:
            self.text.append(data.strip())


def safe_link(value, base):
    try:
        if not isinstance(value, str):
            return None
        url = public_https(urljoin(base, value))
        parts = urlsplit(url)
        # Remove only known tracking parameters, retaining event-identifying queries.
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
        return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or '/', urlencode(query), ''))
    except (ValueError, TypeError):
        return None


def date_value(value, issues, field):
    if not value:
        return None
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}.*)?', value):
        issues.append(f'invalid_{field}'); return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if len(value) > 10 and parsed.tzinfo is None:
            issues.append(f'timezone_missing_{field}'); return None
    except ValueError:
        issues.append(f'invalid_{field}'); return None
    if len(value) == 10:
        issues.append(f'day_precision_{field}')
        # Preserve raw day in evidence; reviewer resolves time before publication.
        return None
    return value


def objects(value, depth=0):
    if depth > 10:
        return
    if isinstance(value, list):
        for item in value[:1000]:
            yield from objects(item, depth + 1)
    elif isinstance(value, dict):
        types = value.get('@type', [])
        types = [types] if isinstance(types, str) else types
        if isinstance(types, list) and any(t in ('Event', 'Hackathon', 'EducationEvent', 'BusinessEvent') for t in types):
            yield value
        if '@graph' in value:
            yield from objects(value['@graph'], depth + 1)


def structured(item, base):
    title = item.get('name') or item.get('title')
    description = item.get('description')
    title = title if isinstance(title, str) else ''
    description = description if isinstance(description, str) else ''
    if not KEYWORD.search(title + ' ' + description):
        return None
    issues = []
    organizer = item.get('organizer')
    organizer = organizer.get('name') if isinstance(organizer, dict) else organizer
    location = item.get('location', {})
    address = location.get('address', {}) if isinstance(location, dict) else {}
    city = address.get('addressLocality') if isinstance(address, dict) else None
    state = address.get('addressRegion') if isinstance(address, dict) else None
    mode = {'https://schema.org/OnlineEventAttendanceMode': 'Online',
            'https://schema.org/OfflineEventAttendanceMode': 'In-Person',
            'https://schema.org/MixedEventAttendanceMode': 'Hybrid'}.get(item.get('eventAttendanceMode'))
    return dict(title=title[:255], description=description[:20000] or None,
        organization=organizer if isinstance(organizer, str) else None,
        url=safe_link(item.get('url', base), base), location=city, state=state, mode=mode,
        start_date=date_value(item.get('startDate'), issues, 'start_date'),
        end_date=date_value(item.get('endDate'), issues, 'end_date'),
        registration_deadline=date_value(item.get('registrationDeadline'), issues, 'registration_deadline'),
        registration_url=safe_link(item.get('registrationUrl'), base),
        eligibility=item.get('eligibility') if isinstance(item.get('eligibility'), str) else None,
        prize=item.get('prize') if isinstance(item.get('prize'), str) else None,
        _issues=issues, _raw_dates={k: item.get(k) for k in ('startDate', 'endDate', 'registrationDeadline') if item.get(k)})


def extract(content, adapter, url):
    if len(content.encode()) > 2_000_000:
        raise ValueError('document_too_large')
    items = []
    if adapter == 'events-json-v1':
        raw = json.loads(content)
        if isinstance(raw, dict) and isinstance(raw.get('events'), list):
            items = raw['events']
        else:
            items = list(objects(raw))
    elif adapter == 'official-html-v1':
        page = Page(); page.feed(content)
        for script in page.scripts[:100]:
            try:
                items.extend(objects(json.loads(script)))
            except (ValueError, RecursionError):
                continue
        if not items:
            text = ' '.join(page.text)
            if KEYWORD.search(text):
                return [dict(title=text[:255], description=text[:20000], url=url,
                    _issues=['unstructured_page', 'manual_field_extraction_required'])]
    elif adapter in ('rss-v1', 'sitemap-v1'):
        root = ElementTree.fromstring(content)
        if adapter == 'sitemap-v1':
            urls = [node.text for node in root.iter() if node.tag.split('}')[-1] == 'loc']
            return [dict(title='Hackathon link awaiting verification', url=link,
                _issues=['sitemap_link_only', 'manual_field_extraction_required'])
                for value in urls[:1000] if value and KEYWORD.search(value)
                if (link := safe_link(value, url))]
        for entry in root.iter():
            if entry.tag.split('}')[-1] not in ('item', 'entry'):
                continue
            fields = {}
            for child in entry:
                key = child.tag.split('}')[-1]
                fields[key] = child.attrib.get('href') or ''.join(child.itertext())
            items.append(dict(name=fields.get('title'), description=fields.get('description') or fields.get('summary'), url=fields.get('link')))
    else:
        raise ValueError('unsupported_adapter')
    if len(items) > 1000:
        raise ValueError('too_many_announcements')
    return [row for item in items if isinstance(item, dict) and (row := structured(item, url))]
